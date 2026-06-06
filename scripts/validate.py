"""
Validation script — generates styled P(t), E(t), SoC(t) and strategic-indicator
plots plus the per-phase error table for the synthetic simulation scenario,
overlaying the model output against the direct analytical computation.
"""
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from src.domain.battery import Battery
from src.domain.dtos import UpdateRequestDto
from src.domain.energy_model import EnergyModel
from src.domain.vehicle_energy_system import VehicleEnergySystem

DT = 0.1
TOTAL_TIME = 60.0
MASS = 1500
CD = 0.3
A = 2.2
CR = 0.015
RHO = 1.225
G = 9.81

INK = "#16181d"
ORANGE = "#ff6a00"
GRAPHITE = "#5b6470"
ACCEL = "#2ecc71"
CRUISE = "#3a7bd5"
BRAKE = "#e74c3c"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 12.5,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.labelsize": 10,
    "axes.labelcolor": INK,
    "axes.edgecolor": "#b9bec7",
    "axes.linewidth": 1.0,
    "xtick.color": GRAPHITE,
    "ytick.color": GRAPHITE,
    "axes.grid": True,
    "grid.color": "#e9ebef",
    "grid.linewidth": 1.0,
    "legend.frameon": True,
    "legend.framealpha": 0.95,
    "legend.edgecolor": "#d4d8df",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


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


def _phase_bands(ax) -> None:
    ax.axvspan(0, 15, color=ACCEL, alpha=0.07)
    ax.axvspan(15, 40, color=CRUISE, alpha=0.07)
    ax.axvspan(40, 60, color=BRAKE, alpha=0.07)


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

    fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
    fig.suptitle(
        "Validação do Modelo Energético — Modelo vs. Cálculo Analítico",
        fontsize=15, fontweight="bold", color=INK, y=0.98,
    )

    ax = axes[0][0]
    _phase_bands(ax)
    ax.plot(time_arr, [p / 1000 for p in power_analytical], "-", label="Analítico",
            linewidth=5.5, color=ORANGE, alpha=0.35, solid_capstyle="round")
    ax.plot(time_arr, [p / 1000 for p in power_model], "-", label="Modelo",
            linewidth=1.8, color=INK)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Potência (kW)")
    ax.set_title("Potência Instantânea  P(t)")
    ax.legend(loc="upper right")
    ax.axhline(y=0, color=GRAPHITE, linewidth=0.8)

    ax = axes[0][1]
    _phase_bands(ax)
    ax.plot(time_arr, [e / 1000 for e in energy_analytical_arr], "-", label="Analítico",
            linewidth=5.5, color=ORANGE, alpha=0.35, solid_capstyle="round")
    ax.plot(time_arr, [e / 1000 for e in energy_model_arr], "-", label="Modelo",
            linewidth=1.8, color=INK)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Energia (kJ)")
    ax.set_title("Energia Mecânica Acumulada  E(t)")
    ax.legend(loc="lower right")

    ax = axes[1][0]
    _phase_bands(ax)
    ax.plot(time_arr, [s * 100 for s in soc_arr], linewidth=2.4, color=ORANGE)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("SoC (%)")
    ax.set_title("Estado de Carga  SoC(t)")

    ax = axes[1][1]
    _phase_bands(ax)
    ax2 = ax.twinx()
    ln1 = ax.plot(time_arr, autonomy_arr, label="Autonomia (s)", linewidth=2.2, color=CRUISE)
    ln2 = ax2.plot(time_arr, [c * 1000 for c in consumption_arr], label="Consumo (Wh/km)",
                   linewidth=2.2, color=ORANGE)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Autonomia estimada (s)")
    ax2.set_ylabel("Consumo específico (Wh/km)")
    ax.set_title("Indicadores Estratégicos")
    lns = ln1 + ln2
    ax.legend(lns, [line.get_label() for line in lns], loc="center right")
    ax2.grid(False)

    fig.text(
        0.5, 0.012,
        f"Aceleração   ·   Cruzeiro   ·   Frenagem regenerativa        "
        f"Modelo ≡ Analítico  —  erro total = {total_error:.4f}%",
        ha="center", fontsize=11, color=INK,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff3e9", edgecolor=ORANGE, linewidth=1.2),
    )

    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig("docs/validation_plots.png", dpi=170, bbox_inches="tight", facecolor="white")
    print("Gráficos salvos em docs/validation_plots.png")


if __name__ == "__main__":
    main()
