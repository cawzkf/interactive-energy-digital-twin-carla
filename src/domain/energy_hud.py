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
        
    def render(self) -> None:
        """
        Desenha o painel de HUD na superfície pygame.

        Deve ser chamado após update() e antes de pygame.display.flip().
        Não levanta exceção se nenhum dado foi recebido ainda — apenas
        exibe "Aguardando dados..." até o primeiro tick completo.
        """
        lines = self._build_lines()
        self._draw_panel(lines)
    
    def _build_lines(self) -> list[tuple[str, tuple[int, int, int]]]:
        """
        Monta a lista de (texto, cor) que será renderizada no painel.

        Retorna
        -------
        list[tuple[str, tuple]]
            Cada item é um par (string, cor RGB).
        """
        if self._last_response is None:
            return [("  Aguardando dados...", COLOR_WHITE)]

        r = self._last_response

        # ── Velocidade (não vem no DTO, mas pode ser inferida / exibida
        #    pelo CarlaClient antes de criar o DTO; aqui exibimos o que temos)

        # ── Potência
        power_w   = r.power
        power_kw  = power_w / 1_000.0
        if power_w > 0:
            power_label = f"  Potência:       {power_kw:+.2f} kW  [DESCARGA]"
            power_color = COLOR_GREEN
        elif power_w < 0:
            power_label = f"  Potência:       {power_kw:+.2f} kW  [REGEN]"
            power_color = COLOR_CYAN
        else:
            power_label = f"  Potência:        0.00 kW"
            power_color = COLOR_WHITE

        # ── Energia mecânica acumulada
        energy_j   = r.mech_energy_total
        energy_kwh = energy_j / 3_600_000.0
        energy_label = (
            f"  Energia mec.:  {energy_j:,.0f} J"
            f"  ({energy_kwh:.4f} kWh)"
        )

        # ── Energia elétrica do passo atual
        elec_j     = r.electrical_used_or_recovered
        elec_kwh   = elec_j / 3_600_000.0
        if power_w > 0:
            elec_label = f"  Elétrica usada: {elec_j:,.1f} J  ({elec_kwh:.6f} kWh)"
            elec_color = COLOR_GREEN
        else:
            elec_label = f"  Elétrica recup: {elec_j:,.1f} J  ({elec_kwh:.6f} kWh)"
            elec_color = COLOR_CYAN

        # ── SoC com barra visual
        soc_pct = r.soc * 100.0
        bar     = self._soc_bar(r.soc, width=16)
        soc_label = f"  SoC:  {bar} {soc_pct:5.1f} %"
        if soc_pct < 5:
            soc_color = COLOR_RED
        elif soc_pct < 20:
            soc_color = COLOR_ORANGE
        else:
            soc_color = COLOR_WHITE

        return [
            ("─── Digital Twin — Energia ───", COLOR_YELLOW),
            (power_label,                       power_color ),
            (energy_label,                      COLOR_WHITE ),
            (elec_label,                        elec_color  ),
            ("",                                COLOR_WHITE ),   # separador
            (soc_label,                         soc_color   ),
            ("──────────────────────────────",  COLOR_YELLOW),
        ]

    
    @staticmethod
    def _soc_bar(soc: float, width: int = 16) -> str:
        """
        Gera uma barra de progresso ASCII proporcional ao SoC.

        Parâmetros
        ----------
        soc : float
            Estado de carga normalizado (0.0 a 1.0).
        width : int
            Número total de caracteres da barra.

        Retorna
        -------
        str
            String do tipo '[████░░░░░░]'.
        """
        filled = int(round(soc * width))
        filled = max(0, min(filled, width))
        bar    = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"
