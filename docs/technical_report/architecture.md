# System Architecture

## Overview

This project implements an energy-aware Digital Twin integrated with the CARLA simulator.  
The architecture follows a simplified Clean Architecture approach to ensure separation of concerns, modularity and testability.

The system is organized in layered form to isolate the mathematical energy model, vehicle energy system coordination and battery dynamics from simulation and infrastructure concerns.

---

## Architectural Structure

```bash
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
```

---

## Architectural Layers

### 1. Domain Layer

Contains the core mathematical and physical model of the Digital Twin.

#### Responsibilities

- Longitudinal force modeling  
- Power computation  
- Discrete energy integration  
- Battery state-of-charge management  
- Vehicle energy system coordination  
- Internal state management (accumulated energy, SoC)  
- Structured data transfer via DTOs  

#### Domain Components

- `energy_model.py` – longitudinal traction and power model  
- `vehicle_energy_system.py` – coordinates vehicle-level energy behavior  
- `battery.py` – battery discharge and regeneration modeling  
- `dtos.py` – structured request/response data models  

#### Restrictions

- Must not import CARLA  
- Must not depend on infrastructure  
- Must not depend on logging  
- Must be executable independently  

---

### 2. Application Layer

Coordinates system execution.

#### Responsibilities

- Receives simulation data  
- Converts raw simulator data into structured DTOs  
- Invokes the energy model and vehicle energy system  
- Manages execution loop  
- Coordinates battery and energy updates  
- Sends results to logging  

This layer connects infrastructure to domain without coupling them.

---

### 3. Infrastructure Layer

Contains external dependencies.

#### Components

- `carla_client.py`: Handles simulator connection and data acquisition  
- `logger.py`: Handles energy data persistence and tracking  

#### Responsibilities

- Communication with external simulator  
- Data acquisition from CARLA  
- Logging and observability  
- Side effects and I/O operations  

Infrastructure must not contain domain logic.

---

## Execution Flow

```text
CARLA (Infrastructure)
        ↓
TwinService (Application)
        ↓
VehicleEnergySystem / EnergyModel (Domain)
        ↓
Logger (Infrastructure)
```

---

## Dependency Rule

The dependency direction follows:

```
Infrastructure → Application → Domain
```

At the code level, dependency must always point inward:

```
Domain ← Application ← Infrastructure
```

The Domain layer must remain independent of outer layers.

---

## Architectural Rationale

Clean Architecture was adopted to:

- Ensure domain independence from CARLA  
- Enable offline validation of the energy model  
- Support future extensibility  
- Maintain separation between computation and simulation  
- Allow evolution toward more advanced Digital Twin and CPS-oriented implementations  
- Support battery-aware energy modeling beyond pure longitudinal mechanics  