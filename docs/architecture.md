# System Architecture

## Overview

This project implements an energy-aware Digital Twin integrated with the CARLA simulator.  
The architecture follows a simplified Clean Architecture approach to ensure separation of concerns, modularity and testability.

---

## Architectural Structure

```bash
interactive-energy-digital-twin-carla/
│
├── src/
│   ├── domain/
│   │   └── energy_model.py
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

# Architectural Layers

## 1. Domain Layer

Contains the core mathematical model.

### Responsibilities

- Longitudinal force modeling
- Power computation
- Discrete energy integration
- Internal state management

### Restrictions

- Must not import CARLA
- Must not depend on infrastructure
- Must be executable independently

---

## 2. Application Layer

Coordinates system execution.

### Responsibilities

- Receives simulation data
- Invokes the energy model
- Manages execution loop
- Sends results to logging

This layer connects infrastructure to domain without coupling them.

---

## 3. Infrastructure Layer

Contains external dependencies.

### Components

- `carla_client.py`: Handles simulator connection and data acquisition
- `logger.py`: Handles energy data persistence and tracking

---

# Execution Flow

```text
CARLA (Infrastructure)
        ↓
TwinService (Application)
        ↓
EnergyModel (Domain)
        ↓
Logger (Infrastructure)

---

# Execution Flow

```text
CARLA (Infrastructure)
        ↓
TwinService (Application)
        ↓
EnergyModel (Domain)
        ↓
Logger (Infrastructure)
```

---

# Dependency Rule

The dependency direction follows:

Infrastructure → Application → Domain

The Domain layer must remain independent of outer layers.

---

# Architectural Rationale

Clean Architecture was adopted to:

- Ensure domain independence from CARLA
- Enable offline validation of the energy model
- Support future extensibility
- Maintain separation between computation and simulation

