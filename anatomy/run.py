

"""
Body original:
https://raw.githubusercontent.com/google-deepmind/mujoco/main/model/humanoid/humanoid.xml"""
import mujoco
import mujoco.viewer
import numpy as np

model = mujoco.MjModel.from_xml_path("humanoid.xml")
data  = mujoco.MjData(model)

print("=== SANITY CHECKS ===")
print("nq:", model.nq)
print("nv:", model.nv)
print("nu (actuators):", model.nu)

print("\nActuator names:")
for i in range(model.nu):
    print(i, mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i))


TORSO_PITCH_JOINT = mujoco.mj_name2id(
    model, mujoco.mjtObj.mjOBJ_JOINT, "abdomen_y"
)
torso_qadr = model.jnt_qposadr[TORSO_PITCH_JOINT]
torso_vadr = model.jnt_dofadr[TORSO_PITCH_JOINT]

print("\n=== JOINT INDEX CHECK ===")
print("abdomen_y joint id:", TORSO_PITCH_JOINT)
print("abdomen_y qadr:", torso_qadr)
print("abdomen_y vadr:", torso_vadr)

print("abdomen_y name:",
      mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, TORSO_PITCH_JOINT))


def hip_balance_control(model, data, kp=10.0, kd=1.0):
    torso_angle  = data.qpos[torso_qadr]
    torso_angvel = data.qvel[torso_vadr]

    for side in ("right", "left"):
        aid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"hip_y_{side}"
        )

        data.ctrl[aid] = -kp * torso_angle - kd * torso_angvel


def ankle_balance_control(model, data, kp=3.0, kd=0.3):
    """
    Human-like ankle strategy:
    apply small torques at ankle_x to stabilize upright standing.
    Motors exist in your XML with names:
      ankle_x_right, ankle_x_left
    """
    for side in ("right", "left"):
        jname = f"ankle_x_{side}"
        aname = f"ankle_x_{side}"

        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aname)

        qadr = model.jnt_qposadr[jid]
        vadr = model.jnt_dofadr[jid]

        angle  = data.qpos[qadr]   # rad
        angvel = data.qvel[vadr]   # rad/s

        # PD toward 0 angle
        data.ctrl[aid] = -kp * angle - kd * angvel


# ----------------------------
# SET INITIAL POSE (IMPORTANT)
# ----------------------------

# Load keyframe: stand (upright start)
key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "stand")

if key_id == -1:
    raise RuntimeError("Keyframe 'stand' not found in humanoid.xml")

mujoco.mj_resetDataKeyframe(model, data, key_id)
mujoco.mj_forward(model, data)
data.qvel[:] = 0.0

print("\n=== INITIAL STATE ===")
print("root pos:", data.qpos[0:3])
print("root quat:", data.qpos[3:7])

print("abdomen_y angle:", data.qpos[torso_qadr])
print("abdomen_y vel:", data.qvel[torso_vadr])

# Make sure forward kinematics are consistent
mujoco.mj_forward(model, data)



# ----------------------------
# RUN SIMULATION
# ----------------------------
step = 0

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        data.ctrl[:] = 0.0

        ankle_balance_control(model, data)
        hip_balance_control(model, data)

        if step % 50 == 0:
            print("\n=== STEP", step, "===")
            print("torso angle:", data.qpos[torso_qadr])
            print("torso angvel:", data.qvel[torso_vadr])
            print("root quat:", data.qpos[3:7])
            print("num contacts:", data.ncon)
            for i in range(data.ncon):
                c = data.contact[i]
                g1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom1)
                g2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom2)
                print(f"contact {i}: {g1} <-> {g2}")

            for side in ("right", "left"):
                aid = mujoco.mj_name2id(
                    model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"hip_y_{side}"
                )
                print(f"hip_y_{side} ctrl:", data.ctrl[aid])

                aid = mujoco.mj_name2id(
                    model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"ankle_x_{side}"
                )
                print(f"ankle_x_{side} ctrl:", data.ctrl[aid])
            for foot in ("foot_right", "foot_left"):
                bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, foot)
                linvel = data.cvel[6 * bid + 3:6 * bid + 6]
                print(f"{foot} linvel:", linvel)

        mujoco.mj_step(model, data)
        viewer.sync()
        step += 1

