from carla import Client, VehicleControl

from src.domain.dtos import UpdateRequestDto


class CarlaClient:
    """
    Infrastructure adapter responsible for:
    - Connecting to CARLA
    - Spawning a vehicle
    - Advancing simulation ticks
    - Returning longitudinal vehicle states
    """

    def __init__(self, host: str = "localhost", port: int = 2000) -> None:
        self.client = Client(host, port)
        self.client.set_timeout(10.0)

        self.world = None
        self.map = None
        self.vehicle = None

    def connect(self, fixed_dt: float = 0.1) -> None:
        """
        Connect to CARLA server and enable synchronous mode.

        :param fixed_dt: Simulation time step in seconds
        """
        self.world = self.client.get_world()

        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = fixed_dt

        self.world.apply_settings(settings)

    def spawn_vehicle(self, blueprint_name: str = "vehicle.audi.tt") -> None:
        """
        Spawn vehicle at first available spawn point.
        """
        if self.world is None:
            raise RuntimeError("World not initialized. Call connect() first.")

        self.map = self.world.get_map()
        spawn_points = self.map.get_spawn_points()

        if not spawn_points:
            raise RuntimeError("No spawn points available.")

        blueprint_library = self.world.get_blueprint_library()
        blueprint = blueprint_library.find(blueprint_name)

        if blueprint is None:
            raise RuntimeError(f"Blueprint '{blueprint_name}' not found.")

        self.vehicle = self.world.spawn_actor(blueprint, spawn_points[0])

    def apply_control(
        self,
        throttle: float = 0.5,
        steer: float = 0.0,
        brake: float = 0.0,
    ) -> None:
        """
        Apply control to the vehicle.
        """
        if self.vehicle is None:
            raise RuntimeError("Vehicle not initialized.")

        control = VehicleControl(
            throttle=throttle,
            steer=steer,
            brake=brake,
        )
        self.vehicle.apply_control(control)

    def tick(self) -> UpdateResponseDto:
        """
        Simulation one step and return longitudinal state.

        :return:
            {
                "dt": float,
                "velocity": float,
                "acceleration": float
            }
        """
        if self.world is None or self.vehicle is None:
            raise RuntimeError("Client not fully initialized.")

        snapshot = self.world.tick()
        dt = snapshot.timestamp.delta_seconds

        vel_vec = self.vehicle.get_velocity()
        acc_vec = self.vehicle.get_acceleration()
        forward = self.vehicle.get_transform().get_forward_vector()

        velocity = (
            vel_vec.x * forward.x +
            vel_vec.y * forward.y +
            vel_vec.z * forward.z
        )

        acceleration = (
            acc_vec.x * forward.x +
            acc_vec.y * forward.y +
            acc_vec.z * forward.z
        )

        return UpdateRequestDto(
            velocity=velocity,
            acceleration=acceleration,
            dt=dt,
        )

    def destroy(self) -> None:
        """
        Destroy vehicle and restore asynchronous mode.
        """
        if self.vehicle is not None:
            self.vehicle.destroy()
            self.vehicle = None

        if self.world is not None:
            settings = self.world.get_settings()
            settings.synchronous_mode = False
            settings.fixed_delta_seconds = None
            self.world.apply_settings(settings)

            self.world = None