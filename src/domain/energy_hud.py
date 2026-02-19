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
