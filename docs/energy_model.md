# Longitudinal Energy Model

## 1. Objective

Define a simplified longitudinal vehicle model for real-time energy estimation within a Digital Twin integrated with CARLA.

The model estimates:

- Instantaneous mechanical power
- Accumulated energy consumption

---

## 2. Modeling Assumptions

- One-dimensional longitudinal motion
- Flat road (no slope)
- Constant vehicle parameters
- No drivetrain efficiency modeling
- No regenerative braking modeling
- No thermal effects

---

## 3. Variables

### Time-dependent variables

- v(t): longitudinal velocity [m/s]
- a(t): longitudinal acceleration [m/s²]
- P(t): instantaneous power [W]
- E(t): accumulated energy [J]

---

## 4. Parameters

- m: vehicle mass [kg]
- ρ: air density [kg/m³]
- Cd: aerodynamic drag coefficient [-]
- A: frontal area [m²]
- Cr: rolling resistance coefficient [-]
- g: gravitational acceleration (9.81 m/s²)

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

---

## 8. Energy Model

### 8.1 Continuous Form

E(t) = ∫ P(t) dt

---

### 8.2 Discrete Computational Form

For numerical implementation:

Eₖ₊₁ = Eₖ + Pₖ · Δt

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

The EnergyModel class should:

- Store vehicle parameters
- Maintain internal accumulated energy state
- Implement update(v, a, dt)
- Return instantaneous power and accumulated energy

---

## 11. Model Limitations

- No road grade modeling
- No regenerative braking
- No drivetrain efficiency losses
- No lateral dynamics
- No battery behavior modeling
