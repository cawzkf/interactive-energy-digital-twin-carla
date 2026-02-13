# Longitudinal Energy Model

## 1. Objective

Define a simplified longitudinal vehicle model for real-time energy estimation within a Digital Twin integrated with CARLA.

The model estimates:

- Instantaneous mechanical power
- Accumulated mechanical energy
- Battery state-of-charge variation (SoC)
- Electrical energy consumed or recovered

---

## 2. Modeling Assumptions

- One-dimensional longitudinal motion
- Flat road (no slope)
- Constant vehicle parameters
- Simplified drivetrain representation
- Regenerative braking modeled in simplified form
- No thermal effects

---

## 3. Variables

### Time-dependent variables

- v(t): longitudinal velocity [m/s]
- a(t): longitudinal acceleration [m/s²]
- P(t): instantaneous mechanical power [W]
- E_mech(t): accumulated mechanical energy [J]
- E_elec(t): electrical energy exchanged with battery [J]
- SoC(t): battery state of charge [-]

---

## 4. Parameters

- m: vehicle mass [kg]
- ρ: air density [kg/m³]
- Cd: aerodynamic drag coefficient [-]
- A: frontal area [m²]
- Cr: rolling resistance coefficient [-]
- g: gravitational acceleration (9.81 m/s²)
- η_drive: drivetrain efficiency (simplified)
- η_regen: regenerative efficiency (simplified)
- E_batt: nominal battery energy capacity [J]

---

## 5. Force Modeling

### 5.1 Inertial Force

F_inertial = m · a(t)

### 5.2 Aerodynamic Drag

F_aero = 0.5 · ρ · Cd · A · v(t)²

### 5.3 Rolling Resistance

F_roll = Cr · m · g

---

## 6. Total Equivalent Longitudinal Force

F_total(t) = m·a(t) + 0.5·ρ·Cd·A·v(t)² + Cr·m·g

This represents the equivalent mechanical force required to sustain the observed motion state.

---

## 7. Power Model

P(t) = F_total(t) · v(t)

Expanded form:

P(t) = v(t) · [m·a(t) + 0.5·ρ·Cd·A·v(t)² + Cr·m·g]

When P(t) > 0 → traction power (battery discharge)  
When P(t) < 0 → regenerative braking (battery charge)

---

## 8. Energy Model

### 8.1 Continuous Form

E_mech(t) = ∫ P(t) dt

---

### 8.2 Discrete Computational Form

For numerical implementation:

E_mechₖ₊₁ = E_mechₖ + Pₖ · Δt

Electrical energy exchanged with battery:

If Pₖ > 0:

E_elec = Pₖ / η_drive

If Pₖ < 0:

E_elec = Pₖ · η_regen

Battery state-of-charge update:

SoCₖ₊₁ = SoCₖ − (E_elec / E_batt)

Where:

- Δt: sampling interval
- k: discrete time index

---

## 9. CARLA Integration Inputs

The model requires:

- Longitudinal velocity v
- Longitudinal acceleration a
- Time step Δt

If acceleration is not directly available:

aₖ = (vₖ − vₖ₋₁) / Δt

---

## 10. Conceptual Class Structure

The system is structured into:

EnergyModel:
- Computes forces and mechanical power
- Integrates mechanical energy

Battery:
- Manages SoC dynamics
- Applies simplified discharge and regeneration logic

VehicleEnergySystem:
- Coordinates EnergyModel and Battery
- Provides unified update(v, a, dt)
- Returns mechanical power, accumulated energy, and SoC

---

## 11. Model Limitations

- No road grade modeling
- Simplified drivetrain efficiency
- Simplified regenerative efficiency
- No thermal effects
- No lateral dynamics
- No detailed electrochemical battery model