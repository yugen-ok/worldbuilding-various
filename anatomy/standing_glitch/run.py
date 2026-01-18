import mujoco
import mujoco.viewer
import numpy as np
import time

model = mujoco.MjModel.from_xml_path("humanoid.xml")
data  = mujoco.MjData(model)

# -------------------------------------------------
# LOAD INITIAL STANDING POSE
# -------------------------------------------------

key_id = mujoco.mj_name2id(
    model, mujoco.mjtObj.mjOBJ_KEY, "stand_on_left_leg"
)
mujoco.mj_resetDataKeyframe(model, data, key_id)

# Make stance roughly symmetric
for jname in ["knee_left", "knee_right"]:
    data.qpos[model.joint(jname).qposadr] *= 0.6

data.qpos[2] = 1.35  # pelvis height
mujoco.mj_forward(model, data)

target_qpos = data.qpos.copy()

# -------------------------------------------------
# DEBUG: ACTUATOR MAP (ONCE)
# -------------------------------------------------

print("\n=== ACTUATOR → JOINT MAP ===")
for i in range(model.nu):
    j_id = model.actuator_trnid[i][0]
    j_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j_id)
    print(f"Actuator {i:2d} controls joint: {j_name}")
print("===========================\n")

# -------------------------------------------------
# COM COMPUTATION (MuJoCo 3.x)
# -------------------------------------------------

def compute_com(model, data):
    total_mass = 0.0
    com = np.zeros(3)
    for i in range(model.nbody):
        m = model.body_mass[i]
        if m > 0:
            com += m * data.xipos[i]
            total_mass += m
    return com / total_mass

# -------------------------------------------------
# SIM LOOP WITH DEBUG PRINTS
# -------------------------------------------------

step = 0
last_print = time.time()

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        # Position control
        for i in range(model.nu):
            j_id = model.actuator_trnid[i][0]
            qadr = model.jnt_qposadr[j_id]
            data.ctrl[i] = target_qpos[qadr]

        mujoco.mj_step(model, data)

        if time.time() - last_print > 0.5:
            last_print = time.time()

            com = compute_com(model, data)
            knee_L = data.qpos[model.joint('knee_left').qposadr[0]]
            knee_R = data.qpos[model.joint('knee_right').qposadr[0]]
            ankle_L = data.qpos[model.joint('ankle_y_left').qposadr[0]]
            ankle_R = data.qpos[model.joint('ankle_y_right').qposadr[0]]

            print(
                f"[step {step:5d}] "
                f"pelvis_z={data.qpos[2]:.3f}  "
                f"COM_z={com[2]:.3f}  "
                f"knee_L={knee_L:.2f}  "
                f"knee_R={knee_R:.2f}  "
                f"ankle_L={ankle_L:.2f}  "
                f"ankle_R={ankle_R:.2f}"
            )

        step += 1
        viewer.sync()
