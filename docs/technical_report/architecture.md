# System Architecture

## Overview

This project implements an energy-aware Digital Twin integrated with the CARLA simulator.

The architecture follows a simplified Clean Architecture approach to ensure:

- Separation of concerns  
- Modular design  
- Testability  
- Future extensibility toward AAS-based Digital Twin integration  

The system isolates:

- The longitudinal energy model  
- Battery dynamics  
- Vehicle-level energy coordination  
- Simulation infrastructure  

This enables independent validation of the mathematical model without dependency on CARLA.

---

## Architectural Structure

interactive-energy-digital-twin-carla/
│
├── src/
│   ├── domain/
│   │   ├── energy_model.py
│   │   ├── vehicle_energy_system.py
│   │   ├── battery.py
│   │   └── dtos.py
│   │
│   ├── application/
│   │   └── twin_service.py
│   │
│   ├── infrastructure/
│   │   ├── carla_client.py
│   │   └── logger.py
│   │
│   └── main.py
│
├── tests/
└── docs/

---

# Architectural Layers

## 1. Domain Layer

The Domain Layer contains the core physical and mathematical logic of the Digital Twin.

It is fully independent from CARLA and any infrastructure concerns.

### Responsibilities

- Longitudinal force modeling
- Mechanical power computation
- Discrete energy integration
- Battery discharge and regeneration
- State-of-charge (SoC) management
- Vehicle-level energy coordination
- Encapsulation of update logic
- Data transport via DTOs

### Components

- energy_model.py  
  Implements the longitudinal vehicle dynamics and mechanical energy computation.

- battery.py  
  Models battery discharge and regenerative behavior including efficiency and SoC tracking.

- vehicle_energy_system.py  
  Coordinates energy model and battery interaction.

- dtos.py  
  Provides structured request and response models between layers.

### Restrictions

The Domain Layer:

- Must not import CARLA
- Must not depend on infrastructure
- Must not perform I/O operations
- Must be executable offline
- Must remain simulator-agnostic

---

## 2. Application Layer

The Application Layer is responsible for orchestration of the Digital Twin lifecycle.

### Component

- twin_service.py (planned orchestration layer)

At the current stage, orchestration is still handled inside main.py.

The twin_service module is reserved for:

- Future integration with BaSyx (AAS)
- Digital Twin state synchronization
- Event publishing
- Data streaming
- Decoupling execution loop from entrypoint

This allows progressive evolution toward a full AAS-compliant Digital Twin architecture.

---

## 3. Infrastructure Layer

Contains all external dependencies and side effects.

### Components

- carla_client.py  
  Handles connection to CARLA, synchronous tick management and longitudinal data extraction.

- logger.py  
  Handles structured logging and observability.

### Responsibilities

- Communication with CARLA simulator
- Data acquisition (velocity, acceleration, dt)
- Execution of control commands
- Logging and monitoring
- External side effects

Infrastructure must not contain domain logic.

---

# Execution Flow (Current Implementation)

CARLA (Infrastructure)
        ↓
main.py (Temporary Orchestration)
        ↓
VehicleEnergySystem (Domain Coordination)
        ↓
EnergyModel + Battery (Domain Core)
        ↓
Logger (Infrastructure)

---

# Execution Flow (Planned Architecture)

CARLA (Infrastructure)
        ↓
TwinService (Application Layer)
        ↓
VehicleEnergySystem (Domain Coordination)
        ↓
EnergyModel + Battery (Domain Core)
        ↓
AAS / BaSyx Integration

---

# Dependency Rule

The dependency direction follows Clean Architecture principles.

Logical dependency:

Infrastructure → Application → Domain

Code-level dependency must always point inward:

Domain ← Application ← Infrastructure

The Domain Layer must remain independent from outer layers.

---

# Energy Model Description

The Digital Twin currently considers simplified longitudinal dynamics in a horizontal plane.

Inclination effects are intentionally ignored at this stage.

## Longitudinal Forces

Rolling resistance:

F_roll = C_r * m * g

Aerodynamic drag:

F_aero = 0.5 * rho * C_d * A * v^2

Total longitudinal force:

F_long = m * a + F_roll + F_aero

Where:

- m = vehicle mass [kg]
- a = longitudinal acceleration [m/s²]
- C_r = rolling resistance coefficient
- g = gravitational acceleration [m/s²]
- rho = air density [kg/m³]
- C_d = aerodynamic drag coefficient
- A = frontal area [m²]
- v = longitudinal velocity [m/s]

Mechanical power:

P = F_long * v

Discrete energy integration:

E_k = E_{k-1} + P_k * dt

---

# Vehicle Energy System

The VehicleEnergySystem coordinates:

- Mechanical power computation
- Step mechanical energy calculation
- Battery discharge when power > 0
- Battery regeneration when power < 0
- SoC updates

Energy and battery logic are intentionally decoupled.

---

# Architectural Rationale

Clean Architecture was adopted to:

- Ensure domain independence from CARLA
- Enable offline validation of the energy model
- Support battery-aware modeling
- Allow future integration with AAS (BaSyx)
- Maintain separation between computation and simulation
- Prepare the system for CPS-oriented Digital Twin evolution

---

# Current Maturity Level

The system currently supports:

- Longitudinal mechanical energy estimation
- Battery discharge and regeneration modeling
- Real-time integration with CARLA
- Structured layered architecture

Future work includes:

- Integration with Asset Administration Shell (AAS)
- TwinService implementation
- Real-time HUD visualization
- Data persistence and streaming
- Extension toward full Digital Twin CPS architecture