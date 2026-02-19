import pygame

import pygame
from src.domain.dtos import UpdateResponseDto

COLOR_WHITE       = (255, 255, 255)
COLOR_BLACK       = (0,   0,   0  )
COLOR_YELLOW      = (255, 215, 0  )   # títulos de seção
COLOR_GREEN       = (0,   200, 80 )   # valores positivos (descarga)
COLOR_CYAN        = (0,   220, 220)   # valores de regeneração
COLOR_ORANGE      = (255, 140, 0  )   # SoC baixo (< 20 %)
COLOR_RED         = (220, 50,  50 )   # SoC crítico (< 5 %)
COLOR_BG          = (20,  20,  20,  160)   # fundo semitransparente (RGBA)


class EnergyHUD:
    def __init__(
            self,
            display: pygame.Surface,
            font_size: int = 18,
            pos: tuple[int, int] = (10, 10),
            panel_width: int = 320,
        ) -> None:
            self.display      = display
            self.pos          = pos
            self.panel_width  = panel_width

            pygame.font.init()
            try:
                self.font = pygame.font.SysFont("monospace", font_size, bold=False)
            except Exception:
                self.font = pygame.font.Font(None, font_size)

            self.line_height  = self.font.get_linesize() + 4   
            self._last_response: UpdateResponseDto | None = None
    
    def update(self, response: UpdateResponseDto) -> None:
        self._last_response = response
            
        