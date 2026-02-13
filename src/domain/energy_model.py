

class EnergyModel:
	def __init__(
			self,
			mass: float,
			drag_coefficient: float,
			frontal_area: float,
			rolling_resistance_coefficient: float,
			air_density: float = 1.225,
			gravity: float = 9.81,
		):
		self.mass = mass
		self.drag_coefficient = drag_coefficient
		self.frontal_area = frontal_area
		self.rolling_resistance_coefficient =	rolling_resistance_coefficient
		self.air_density = air_density
		self.gravity =  gravity
		self.energy : float  = 0.0

	def update(
			self,
			velocity: float,
			acceleration: float,
			dt: float
		) -> tuple[float,float]:
		
		if dt <= 0:
		 raise ValueError("dt must be positive")
	
		
		f_inertial = self.mass * acceleration
		
		f_aero = (
		0.5 * self.air_density 
		* self.drag_coefficient * self.frontal_area
		* velocity ** 2
		)
		
		f_roll = (
		self.rolling_resistance_coefficient
		* self.mass * self.gravity
		)
		
		f_total = f_inertial + f_aero + f_roll
		
		power = f_total * velocity
		
		if power > 0:
			self.energy += power * dt
		
		return power, self.energy
