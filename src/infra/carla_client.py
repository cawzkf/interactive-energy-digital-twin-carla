from carla import Client, Location, Rotation, Transform, VehicleControl
from src.domain.dtos import UpdateRequestDto
from src.infra.config import AcquisitionConfig

MAX_LONG_ACCEL = 3.0
ACCEL_EMA_ALPHA = 0.15


class CarlaClient:
    """
    Infrastructure adapter responsible for:
    - Connecting to CARLA
    - Spawning a vehicle
    - Advancing simulation ticks
    - Returning longitudinal vehicle states
    """

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        host = host or AcquisitionConfig.CARLA_HOST
        port = port or AcquisitionConfig.CARLA_PORT
        self.client = Client(host, port)
        self.client.set_timeout(50.0)

        self.world = None
        self.map = None
        self.vehicle = None
        self.spectator = None
        self.traffic_manager = None
        self._prev_velocity = 0.0
        self._accel_ema = 0.0
        self._autopilot_on = False

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

        self.traffic_manager = self.client.get_trafficmanager()
        self.traffic_manager.set_synchronous_mode(True)
        self.spectator = self.world.get_spectator()

    def _update_spectator(self) -> None:
        """Chase camera: position the spectator behind and above the vehicle."""
        if self.vehicle is None or self.spectator is None:
            return
        tf = self.vehicle.get_transform()
        fwd = tf.get_forward_vector()
        loc = tf.location
        cam = Location(x=loc.x - 6.0 * fwd.x, y=loc.y - 6.0 * fwd.y, z=loc.z + 3.0)
        self.spectator.set_transform(Transform(cam, Rotation(pitch=-15.0, yaw=tf.rotation.yaw)))

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
        self.set_autopilot(True)

    def set_autopilot(self, enabled: bool) -> None:
        """Enable/disable Traffic Manager autopilot (no-op if unchanged)."""
        if self.vehicle is None or self._autopilot_on == enabled:
            return
        self.vehicle.set_autopilot(enabled, self.traffic_manager.get_port())
        self._autopilot_on = enabled

    def apply_manual(
        self, throttle: float, steer: float, brake: float, reverse: bool = False
    ) -> None:
        """Apply manual driving control (turns autopilot off)."""
        if self.vehicle is None:
            return
        self.set_autopilot(False)
        self.vehicle.apply_control(
            VehicleControl(throttle=throttle, steer=steer, brake=brake, reverse=reverse)
        )

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

    def tick(self) -> UpdateRequestDto:
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

        self.world.tick()
        snapshot = self.world.get_snapshot()
        dt = snapshot.timestamp.delta_seconds

        self._update_spectator()

        vel_vec = self.vehicle.get_velocity()
        transform = self.vehicle.get_transform()
        forward = transform.get_forward_vector()
        location = transform.location

        velocity = (
            vel_vec.x * forward.x +
            vel_vec.y * forward.y +
            vel_vec.z * forward.z
        )
        if abs(velocity) < 0.05:
            velocity = 0.0

        raw_accel = (velocity - self._prev_velocity) / dt if dt > 0 else 0.0
        self._prev_velocity = velocity
        self._accel_ema = (
            ACCEL_EMA_ALPHA * raw_accel + (1 - ACCEL_EMA_ALPHA) * self._accel_ema
        )
        acceleration = max(-MAX_LONG_ACCEL, min(MAX_LONG_ACCEL, self._accel_ema))

        return UpdateRequestDto(
            velocity=velocity,
            acceleration=acceleration,
            dt=dt,
            x=location.x,
            y=location.y,
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
