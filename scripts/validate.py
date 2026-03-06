"""
Validation script — generates P(t), E(t), SoC(t) plots and error table
for the synthetic simulation scenario.
"""
import math
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.domain.dtos import UpdateRequestDto

DT = 0.1
TOTAL_TIME = 60.0
MASS = 1500
CD = 0.3
A = 2.2
CR = 0.015
RHO = 1.225
G = 9.81


def velocity_profile(t: float) -> tuple[float, float]:
    if t < 15:
        acc = 2.0
        vel = acc * t
    elif t < 40:
        acc = 0.0
        vel = 30.0
    else:
        acc = -1.5
        vel = max(0.0, 30.0 + acc * (t - 40))
        if vel == 0.0:
            acc = 0.0
    return vel, acc


def analytical_power(v: float, a: float) -> float:
    f_inertial = MASS * a
    f_aero = 0.5 * RHO * CD * A * v ** 2
    f_roll = CR * MASS * G
    return (f_inertial + f_aero + f_roll) * v


def main():
    energy_model = EnergyModel(
        mass=MASS,
        drag_coefficient=CD,
        frontal_area=A,
        rolling_resistance_coefficient=CR,
    )
    battery = Battery(
        capacity=50_000_000,
        soc_init=1.0,
        efficiency_discharge=0.9,
        efficiency_regen=0.9,
    )
    system = VehicleEnergySystem(energy_model, battery)

    steps = int(TOTAL_TIME / DT)

    time_arr = []
    vel_arr = []
    power_model = []
    power_analytical = []
    energy_model_arr = []
    energy_analytical_arr = []
    soc_arr = []
    autonomy_arr = []
    consumption_arr = []

    e_analytical = 0.0
    t = 0.0

    for _ in range(steps):
        vel, acc = velocity_profile(t)
        request = UpdateRequestDto(velocity=vel, acceleration=acc, dt=DT)
        resp = system.update(request)

        p_analytical = analytical_power(vel, acc)
        if p_analytical > 0:
            e_analytical += p_analytical * DT

        time_arr.append(t)
        vel_arr.append(vel)
        power_model.append(resp.power)
        power_analytical.append(p_analytical)
        energy_model_arr.append(resp.mech_energy_total)
        energy_analytical_arr.append(e_analytical)
        soc_arr.append(resp.soc)
        autonomy_arr.append(resp.estimated_autonomy)
        consumption_arr.append(resp.specific_consumption)

        t += DT

    # --- Error by phase ---
    phases = [
        ("Aceleração (0-15s)", 0, 15),
        ("Cruzeiro (15-40s)", 15, 40),
        ("Frenagem (40-60s)", 40, 60),
    ]

    print("=" * 65)
    print(f"{'Fase':<25} {'E_modelo (kJ)':>13} {'E_anal (kJ)':>12} {'Erro (%)':>10}")
    print("=" * 65)

    for name, t_start, t_end in phases:
        i_start = int(t_start / DT)
        i_end = int(t_end / DT)

        e_model_phase = energy_model_arr[i_end - 1] - (energy_model_arr[i_start - 1] if i_start > 0 else 0)
        e_anal_phase = energy_analytical_arr[i_end - 1] - (energy_analytical_arr[i_start - 1] if i_start > 0 else 0)

        if e_anal_phase != 0:
            error = abs(e_model_phase - e_anal_phase) / abs(e_anal_phase) * 100
        else:
            error = 0.0

        print(f"{name:<25} {e_model_phase/1000:>13.2f} {e_anal_phase/1000:>12.2f} {error:>10.4f}")

    print("=" * 65)
    e_total_model = energy_model_arr[-1]
    e_total_anal = energy_analytical_arr[-1]
    total_error = abs(e_total_model - e_total_anal) / abs(e_total_anal) * 100 if e_total_anal != 0 else 0
    print(f"{'TOTAL':<25} {e_total_model/1000:>13.2f} {e_total_anal/1000:>12.2f} {total_error:>10.4f}")
    print()

    # --- Plots ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Validação do Modelo Energético — Cenário Sintético", fontsize=14, fontweight="bold")

    # P(t)
    ax = axes[0][0]
    ax.plot(time_arr, [p / 1000 for p in power_model], label="Modelo", linewidth=1.5)
    ax.plot(time_arr, [p / 1000 for p in power_analytical], "--", label="Analítico", linewidth=1.2, alpha=0.8)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Potência (kW)")
    ax.set_title("Potência Instantânea P(t)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="k", linewidth=0.5)
    ax.axvspan(0, 15, alpha=0.05, color="green", label="Aceleração")
    ax.axvspan(15, 40, alpha=0.05, color="blue")
    ax.axvspan(40, 60, alpha=0.05, color="red")

    # E(t)
    ax = axes[0][1]
    ax.plot(time_arr, [e / 1000 for e in energy_model_arr], label="Modelo", linewidth=1.5)
    ax.plot(time_arr, [e / 1000 for e in energy_analytical_arr], "--", label="Analítico", linewidth=1.2, alpha=0.8)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Energia (kJ)")
    ax.set_title("Energia Mecânica Acumulada E(t)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # SoC(t)
    ax = axes[1][0]
    ax.plot(time_arr, [s * 100 for s in soc_arr], linewidth=1.5, color="tab:orange")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("SoC (%)")
    ax.set_title("Estado de Carga SoC(t)")
    ax.grid(True, alpha=0.3)
    ax.axvspan(0, 15, alpha=0.05, color="green")
    ax.axvspan(15, 40, alpha=0.05, color="blue")
    ax.axvspan(40, 60, alpha=0.05, color="red")

    # Autonomy + Consumption
    ax = axes[1][1]
    ax2 = ax.twinx()
    ln1 = ax.plot(time_arr, autonomy_arr, label="Autonomia (s)", linewidth=1.5, color="tab:green")
    ln2 = ax2.plot(time_arr, [c * 1000 for c in consumption_arr], label="Consumo (Wh/km)", linewidth=1.5, color="tab:purple")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Autonomia estimada (s)")
    ax2.set_ylabel("Consumo específico (Wh/km)")
    ax.set_title("Indicadores Estratégicos")
    lns = ln1 + ln2
    labs = [l.get_label() for l in lns]
    ax.legend(lns, labs, loc="center right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("docs/validation_plots.png", dpi=150, bbox_inches="tight")
    print("Gráficos salvos em docs/validation_plots.png")


if __name__ == "__main__":
    main()
