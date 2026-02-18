# Longitudinal Energy Model

## 1. Objective

Define a simplified longitudinal vehicle model for real-time energy estimation within a Digital Twin integrated with CARLA.

The model estimates:

- Instantaneous mechanical power  
- Accumulated mechanical energy  
- Battery state-of-charge variation (SoC)  
- Electrical energy consumed or recovered  

This model is implemented inside the Domain Layer and remains independent from CARLA and infrastructure concerns.

---

# 2. Modeling Assumptions

The following assumptions are adopted to maintain mathematical tractability and real-time capability:

- One-dimensional longitudinal motion  
- Flat road (no slope)  
- Constant vehicle parameters  
- Simplified drivetrain representation  
- Regenerative braking modeled in simplified form  
- No thermal effects  
- No lateral or vertical dynamics  

These assumptions are intentional and define the current maturity level of the Digital Twin.

---

# 3. Time-Dependent Variables

The system evolves in discrete time.

- v(t): longitudinal velocity [m/s]  
- a(t): longitudinal acceleration [m/s²]  
- P(t): instantaneous mechanical power [W]  
- E_mech(t): accumulated mechanical energy [J]  
- E_elec(t): electrical energy exchanged with battery [J]  
- SoC(t): battery state of charge [-]  

Discrete representation:

- vₖ  
- aₖ  
- Pₖ  
- E_mechₖ  
- SoCₖ  

---

# 4. Model Parameters

Vehicle and environmental parameters:

- m: vehicle mass [kg]  
- ρ: air density [kg/m³]  
- C_d: aerodynamic drag coefficient [-]  
- A: frontal area [m²]  
- C_r: rolling resistance coefficient [-]  
- g: gravitational acceleration (9.81 m/s²)  

Battery parameters:

- η_drive: drivetrain discharge efficiency  
- η_regen: regenerative efficiency  
- E_batt: nominal battery energy capacity [J]  

All parameters are treated as constant in the current model.

---

# 5. Longitudinal Force Modeling

The total equivalent longitudinal force required to sustain the vehicle motion state is composed of:

## 5.1 Inertial Force

F_inertial = m · a(t)

## 5.2 Aerodynamic Drag

F_aero = 0.5 · ρ · C_d · A · v(t)²

## 5.3 Rolling Resistance

F_roll = C_r · m · g

---

# 6. Total Longitudinal Force

F_total(t) = m·a(t) + 0.5·ρ·C_d·A·v(t)² + C_r·m·g

This represents the mechanical force equivalent required to reproduce the observed motion.

---

# 7. Mechanical Power Model

Instantaneous mechanical power:

P(t) = F_total(t) · v(t)

Expanded form:

P(t) = v(t) · [m·a(t) + 0.5·ρ·C_d·A·v(t)² + C_r·m·g]

Interpretation:

- If P(t) > 0 → traction power (battery discharge)  
- If P(t) < 0 → regenerative braking (battery charge)  

---

# 8. Energy Model

## 8.1 Continuous Form

E_mech(t) = ∫ P(t) dt

---

## 8.2 Discrete Computational Form

For real-time numerical implementation:

E_mechₖ₊₁ = E_mechₖ + Pₖ · Δt

Where:

- Δt is the sampling interval  
- k is the discrete time index  

Mechanical energy is accumulated only when Pₖ > 0 in the current implementation.

---

# 9. Battery Energy Exchange Model

The electrical energy exchange depends on the sign of mechanical power.

If Pₖ > 0 (traction):

E_elec = (Pₖ · Δt) / η_drive

If Pₖ < 0 (regeneration):

E_elec = |Pₖ · Δt| · η_regen

Battery state-of-charge update:

SoCₖ₊₁ = SoCₖ − (E_elec / E_batt)

Where:

- E_batt is total battery capacity in Joules  
- SoC ∈ [0, 1]  

This battery logic is implemented separately in the Battery class and coordinated by VehicleEnergySystem.

---

# 10. CARLA Integration Inputs

The model requires the following inputs from the simulator:

- Longitudinal velocity v  
- Longitudinal acceleration a  
- Time step Δt  

If acceleration is not directly available:

aₖ = (vₖ − vₖ₋₁) / Δt

The model does not depend on CARLA and can be validated offline using synthetic velocity profiles.

---

# 11. Conceptual Class Structure

The implementation follows domain separation.

EnergyModel:
- Computes longitudinal forces  
- Computes mechanical power  
- Integrates mechanical energy  

Battery:
- Manages SoC dynamics  
- Applies discharge and regenerative efficiency  

VehicleEnergySystem:
- Coordinates EnergyModel and Battery  
- Provides unified update(v, a, dt)  
- Returns mechanical power, accumulated energy, SoC and electrical exchange  

All logic resides inside the Domain Layer.

---

# 12. Model Limitations

The current implementation does not include:

- Road grade modeling  
- Variable drivetrain efficiency  
- Thermal effects  
- Lateral or vertical dynamics  
- Electrochemical battery modeling  
- Motor torque limits  
- Power electronics modeling  

The model is intentionally simplified to prioritize:

- Real-time computation  
- Clean architecture separation  
- Progressive evolution toward a CPS-oriented Digital Twin