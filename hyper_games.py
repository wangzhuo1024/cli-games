#!/usr/bin/env python3
"""
超级复古游戏合集 - Hyper Games
包含7款经典街机游戏的完美复刻：
- 俄罗斯方块 (Tetris)
- 太空侵略者 (Space Invaders)
- 无尽跑酷 (Runner)
- 密码破解 (Crack)
- 直升机 (Chopper)
- 打砖块 (Breakout)
- 高塔堆叠 (Tower)

使用 Rich 库渲染终端图形界面
"""

import os
import sys
import time
import random
import math
import threading
import queue
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Callable
from enum import Enum, auto
from abc import ABC, abstractmethod

# Rich imports
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.style import Style
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

# ANSI 颜色代码
class Colors:
    RESET = '\x1b[0m'
    BOLD = '\x1b[1m'
    DIM = '\x1b[2m'
    BLINK = '\x1b[5m'
    
    # 亮色
    RED = '\x1b[91m'
    GREEN = '\x1b[92m'
    YELLOW = '\x1b[93m'
    BLUE = '\x1b[94m'
    MAGENTA = '\x1b[95m'
    CYAN = '\x1b[96m'
    WHITE = '\x1b[97m'
    
    # 暗色
    DARK_RED = '\x1b[31m'
    DARK_GREEN = '\x1b[32m'
    DARK_YELLOW = '\x1b[33m'
    
    # 背景色
    BG_RED = '\x1b[41m'
    BG_GREEN = '\x1b[42m'
    BG_WHITE = '\x1b[47m'
    BG_GRAY = '\x1b[100m'


# ============================================================================
# 基础工具类
# ============================================================================

def clear_screen():
    """清屏并移动光标到左上角"""
    print('\x1b[2J\x1b[H', end='')

def hide_cursor():
    """隐藏光标"""
    print('\x1b[?25l', end='')

def show_cursor():
    """显示光标"""
    print('\x1b[?25h', end='')

def move_cursor(row: int, col: int) -> str:
    """移动光标到指定位置，返回 ANSI 转义序列"""
    if row < 1:
        row = 1
    if col < 1:
        col = 1
    return f'\x1b[{row};{col}H'

def get_terminal_size() -> Tuple[int, int]:
    """获取终端大小 (cols, rows)"""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except:
        return 80, 24


# ============================================================================
# 游戏控制器基类
# ============================================================================

class GameState(Enum):
    NOT_STARTED = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    LEVEL_COMPLETE = auto()
    VICTORY = auto()


@dataclass
class Particle:
    """粒子效果"""
    x: float
    y: float
    char: str
    color: str
    vx: float
    vy: float
    life: int


@dataclass
class ScorePopup:
    """分数弹出文字"""
    x: float
    y: float
    text: str
    frames: int
    color: str


class GameController(ABC):
    """游戏控制器基类"""
    
    def __init__(self, console: Console):
        self.console = console
        self.running = True
        self.state = GameState.NOT_STARTED
        self.score = 0
        self.high_score = 0
        self.level = 1
        
    @abstractmethod
    def init_game(self):
        """初始化游戏"""
        pass
    
    @abstractmethod
    def update(self):
        """更新游戏状态"""
        pass
    
    @abstractmethod
    def render(self) -> str:
        """渲染游戏画面"""
        pass
    
    @abstractmethod
    def handle_input(self, key: str):
        """处理输入"""
        pass
    
    def stop(self):
        """停止游戏"""
        self.running = False


# ============================================================================
# 俄罗斯方块 (Tetris)
# ============================================================================

# 方块形状定义
TETROMINOES = {
    'I': [
        [[1, 1, 1, 1]],
        [[1], [1], [1], [1]],
    ],
    'O': [
        [[1, 1], [1, 1]],
    ],
    'T': [
        [[0, 1, 0], [1, 1, 1]],
        [[1, 0], [1, 1], [1, 0]],
        [[1, 1, 1], [0, 1, 0]],
        [[0, 1], [1, 1], [0, 1]],
    ],
    'S': [
        [[0, 1, 1], [1, 1, 0]],
        [[1, 0], [1, 1], [0, 1]],
    ],
    'Z': [
        [[1, 1, 0], [0, 1, 1]],
        [[0, 1], [1, 1], [1, 0]],
    ],
    'J': [
        [[1, 0, 0], [1, 1, 1]],
        [[1, 1], [1, 0], [1, 0]],
        [[1, 1, 1], [0, 0, 1]],
        [[0, 1], [0, 1], [1, 1]],
    ],
    'L': [
        [[0, 0, 1], [1, 1, 1]],
        [[1, 0], [1, 0], [1, 1]],
        [[1, 1, 1], [1, 0, 0]],
        [[1, 1], [0, 1], [0, 1]],
    ],
}

PIECE_COLORS = {
    'I': Colors.CYAN,
    'O': Colors.YELLOW,
    'T': Colors.MAGENTA,
    'S': Colors.GREEN,
    'Z': Colors.RED,
    'J': Colors.BLUE,
    'L': Colors.DARK_YELLOW,
}

PIECE_TYPES = list(TETROMINOES.keys())


class TetrisGame(GameController):
    """俄罗斯方块游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.board_width = 12
        self.board_height = 20
        self.board: List[List[str]] = []
        self.current_piece = 'T'
        self.current_rotation = 0
        self.piece_x = 0
        self.piece_y = 0
        self.next_piece = 'T'
        self.level = 1
        self.lines = 0
        self.drop_interval = 1000
        self.drop_counter = 0
        self.game_mode = 'marathon'  # 'marathon' or 'sprint'
        self.selected_mode = 'marathon'
        self.hard_dropping = False
        self.hard_drop_consumed = False
        
        # 特效
        self.particles: List[Particle] = []
        self.shake_frames = 0
        self.shake_intensity = 0
        self.flash_rows: List[int] = []
        self.flash_frames = 0
        self.combo_message = ''
        self.combo_frames = 0
        self.combo_chain = 0
        self.back_to_back_tetris = False
        self.glitch_frame = 0
        
    def init_game(self):
        """初始化游戏"""
        self.board = [[0 for _ in range(self.board_width)] for _ in range(self.board_height)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.drop_interval = 1000
        self.drop_counter = 0
        self.state = GameState.NOT_STARTED
        self.combo_chain = 0
        self.back_to_back_tetris = False
        self.hard_dropping = False
        self.hard_drop_consumed = False
        self.shake_frames = 0
        self.flash_rows = []
        self.flash_frames = 0
        self.combo_message = ''
        self.combo_frames = 0
        self.particles = []
        self.spawn_piece()
        self.next_piece = self.random_piece()
        
    def random_piece(self) -> str:
        """随机生成一个新方块"""
        return random.choice(PIECE_TYPES)
    
    def spawn_piece(self):
        """生成新方块"""
        self.current_piece = self.next_piece or self.random_piece()
        self.next_piece = self.random_piece()
        self.current_rotation = 0
        shape = TETROMINOES[self.current_piece][0]
        self.piece_x = (self.board_width - len(shape[0])) // 2
        self.piece_y = 0
        
        if not self.is_valid_position(self.piece_x, self.piece_y, self.current_rotation):
            self.state = GameState.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score
                
    def get_shape(self, rotation: int = None) -> List[List[int]]:
        """获取当前方块的形状"""
        if rotation is None:
            rotation = self.current_rotation
        rotations = TETROMINOES[self.current_piece]
        return rotations[rotation % len(rotations)]
    
    def is_valid_position(self, x: int, y: int, rotation: int) -> bool:
        """检查位置是否有效"""
        shape = TETROMINOES[self.current_piece][rotation % len(TETROMINOES[self.current_piece])]
        for row in range(len(shape)):
            for col in range(len(shape[row])):
                if shape[row][col]:
                    new_x = x + col
                    new_y = y + row
                    if new_x < 0 or new_x >= self.board_width or new_y >= self.board_height:
                        return False
                    if new_y >= 0 and self.board[new_y][new_x]:
                        return False
        return True
    
    def lock_piece(self):
        """锁定方块"""
        shape = self.get_shape()
        color = PIECE_COLORS[self.current_piece]
        for row in range(len(shape)):
            for col in range(len(shape[row])):
                if shape[row][col]:
                    board_y = self.piece_y + row
                    board_x = self.piece_x + col
                    if 0 <= board_y < self.board_height and 0 <= board_x < self.board_width:
                        self.board[board_y][board_x] = color
        self.clear_lines()
        if self.state != GameState.GAME_OVER:
            self.spawn_piece()
            
    def clear_lines(self):
        """消除满行"""
        rows_to_clear = []
        for row in range(self.board_height - 1, -1, -1):
            if all(cell != 0 for cell in self.board[row]):
                rows_to_clear.append(row)
                
        cleared_lines = len(rows_to_clear)
        if cleared_lines > 0:
            # 触发行消除特效
            self.flash_rows = list(range(cleared_lines))
            self.flash_frames = 8
            
            # 生成粒子效果
            particle_chars = ['█', '▓', '▒', '░', '✦', '✧', '◆', '◇']
            particle_colors = [Colors.RED, Colors.YELLOW, Colors.GREEN, Colors.CYAN, Colors.MAGENTA, Colors.WHITE]
            for row in rows_to_clear:
                for x in range(self.board_width):
                    if random.random() < 0.4:
                        self.particles.append(Particle(
                            x=x * 2, y=row,
                            char=random.choice(particle_chars),
                            color=random.choice(particle_colors),
                            vx=(random.random() - 0.5) * 4,
                            vy=(random.random() - 0.8) * 3,
                            life=15 + int(random.random() * 10)
                        ))
            
            # 连击和背靠背计分
            self.combo_chain += 1
            is_tetris = cleared_lines == 4
            b2b_bonus = 400 * self.level if is_tetris and self.back_to_back_tetris else 0
            combo_bonus = (self.combo_chain - 1) * 50 * self.level if self.combo_chain > 1 else 0
            self.back_to_back_tetris = is_tetris
            
            # 屏幕震动
            self.shake_intensity = cleared_lines + min(2, self.combo_chain - 1)
            self.shake_frames = cleared_lines * 5 + (6 if self.combo_chain > 1 else 4)
            
            # 连击消息
            if is_tetris and b2b_bonus > 0:
                self.combo_message = '⚡ B2B TETRIS! ⚡'
                self.combo_frames = 45
            elif is_tetris:
                self.combo_message = '★ TETRIS! ★'
                self.combo_frames = 40
            elif cleared_lines == 3:
                self.combo_message = 'TRIPLE!'
                self.combo_frames = 25
            elif cleared_lines == 2:
                self.combo_message = 'DOUBLE!'
                self.combo_frames = 20
            else:
                self.combo_message = 'SINGLE!'
                self.combo_frames = 16
                
            if self.combo_chain > 1:
                self.combo_message += f'  COMBO x{self.combo_chain}'
                self.combo_frames = max(self.combo_frames, 24)
            
            # 重建棋盘
            remaining_rows = [row for row in self.board if not all(cell != 0 for cell in row)]
            self.board = [[0 for _ in range(self.board_width)] for _ in range(cleared_lines)] + remaining_rows
            self.flash_rows = list(range(cleared_lines))
            
            # 计分
            points_table = [0, 100, 300, 500, 800]
            points = points_table[min(cleared_lines, 4)] * self.level + combo_bonus + b2b_bonus
            self.score += points
            self.lines += cleared_lines
            
            # 升级
            new_level = self.lines // 10 + 1
            if new_level > self.level:
                self.level = new_level
                self.drop_interval = max(100, 1000 - (self.level - 1) * 100)
            
            # 冲刺模式胜利条件
            if self.game_mode == 'sprint' and self.lines >= 40:
                self.state = GameState.VICTORY
                if self.score > self.high_score:
                    self.high_score = self.score
        else:
            self.combo_chain = 0
            
    def move_left(self):
        """左移"""
        if self.is_valid_position(self.piece_x - 1, self.piece_y, self.current_rotation):
            self.piece_x -= 1
            
    def move_right(self):
        """右移"""
        if self.is_valid_position(self.piece_x + 1, self.piece_y, self.current_rotation):
            self.piece_x += 1
            
    def move_down(self) -> bool:
        """下移"""
        if self.is_valid_position(self.piece_x, self.piece_y + 1, self.current_rotation):
            self.piece_y += 1
            return True
        return False
    
    def hard_drop(self):
        """硬降"""
        if self.hard_dropping or self.hard_drop_consumed:
            return
        self.hard_dropping = True
        self.hard_drop_consumed = True
        
    def rotate(self):
        """旋转"""
        new_rotation = (self.current_rotation + 1) % len(TETROMINOES[self.current_piece])
        if self.is_valid_position(self.piece_x, self.piece_y, new_rotation):
            self.current_rotation = new_rotation
            return
        # 墙踢
        for kick in [-1, 1, -2, 2]:
            if self.is_valid_position(self.piece_x + kick, self.piece_y, new_rotation):
                self.piece_x += kick
                self.current_rotation = new_rotation
                return
                
    def update(self):
        """更新游戏状态"""
        if self.state not in [GameState.PLAYING]:
            return
            
        # 处理硬降动画
        if self.hard_dropping:
            moved = False
            for _ in range(2):
                if self.move_down():
                    self.score += 2
                    moved = True
                else:
                    break
            if not moved:
                self.hard_dropping = False
                self.lock_piece()
            return
        
        # 自然下落
        self.drop_counter += 1
        if self.drop_counter * 25 >= self.drop_interval:
            self.drop_counter = 0
            if not self.move_down():
                self.lock_piece()
        
        # 更新特效计时器
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.flash_frames > 0:
            self.flash_frames -= 1
        if self.combo_frames > 0:
            self.combo_frames -= 1
            
        # 更新粒子
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\x1b[2J\x1b[H'
        cols, rows = get_terminal_size()
        
        # 最小终端尺寸检查
        min_cols = self.board_width * 2 + 4
        min_rows = self.board_height + 5
        if cols < min_cols or rows < min_rows:
            msg1 = 'Terminal too small!'
            msg2 = f'Need: {min_cols}×{min_rows}  Have: {cols}×{rows}'
            hint = 'Make pane larger'
            output += move_cursor(rows//2 - 1, max(1, cols//2 - len(msg1)//2))
            output += f'{Colors.CYAN}{msg1}{Colors.RESET}'
            output += move_cursor(rows//2 + 1, max(1, cols//2 - len(msg2)//2))
            output += f'{Colors.DIM}{msg2}{Colors.RESET}'
            output += move_cursor(rows//2 + 3, max(1, cols//2 - len(hint)//2))
            output += f'{Colors.BOLD}{Colors.CYAN}{hint}{Colors.RESET}'
            return output
        
        # 计算布局
        game_left = max(2, (cols - self.board_width * 2 - 16) // 2)
        game_top = max(2, (rows - self.board_height - 4) // 2)
        
        # 应用屏幕震动
        if self.shake_frames > 0:
            game_left += int((random.random() - 0.5) * self.shake_intensity * 2)
            game_top += int((random.random() - 0.5) * self.shake_intensity)
        
        # 标题
        title = [
            '█ █ █▄█ █▀█ █▀▀ █▀█   ▀█▀ █▀▀ ▀█▀ █▀█ █ █▀',
            '█▀█  █  █▀▀ ██▄ █▀▄    █  ██▄  █  █▀▄ █ ▄█',
        ]
        self.glitch_frame = (self.glitch_frame + 1) % 60
        glitch_offset = int((random.random() * 3) - 1) if self.glitch_frame >= 55 else 0
        title_x = (cols - len(title[0])) // 2 + glitch_offset
        
        if self.glitch_frame >= 55 and self.glitch_frame < 58:
            output += move_cursor(game_top - 2, title_x)
            output += f'{Colors.RED}{title[0]}{Colors.RESET}'
            output += move_cursor(game_top - 1, title_x + 1)
            output += f'{Colors.CYAN}{title[1]}{Colors.RESET}'
        else:
            output += move_cursor(game_top - 2, title_x)
            output += f'{Colors.BOLD}{Colors.CYAN}{title[0]}{Colors.RESET}'
            output += move_cursor(game_top - 1, title_x)
            output += f'{Colors.BOLD}{Colors.CYAN}{title[1]}{Colors.RESET}'
        
        # 绘制游戏边框
        output += move_cursor(game_top, game_left)
        output += f'{Colors.CYAN}╔{"══" * self.board_width}╗{Colors.RESET}'
        for y in range(self.board_height):
            output += move_cursor(game_top + 1 + y, game_left)
            output += f'{Colors.CYAN}║{Colors.RESET}'
            output += move_cursor(game_top + 1 + y, game_left + 1 + self.board_width * 2)
            output += f'{Colors.CYAN}║{Colors.RESET}'
        output += move_cursor(game_top + self.board_height + 1, game_left)
        output += f'{Colors.CYAN}╚{"══" * self.board_width}╝{Colors.RESET}'
        
        # 绘制已锁定的方块
        for y in range(self.board_height):
            is_flashing = self.flash_frames > 0 and y in self.flash_rows
            for x in range(self.board_width):
                cell = self.board[y][x]
                if cell:
                    flash_color = f'{Colors.BG_WHITE}{Colors.WHITE}' if is_flashing and self.flash_frames % 2 == 0 else cell
                    output += move_cursor(game_top + 1 + y, game_left + 1 + x * 2)
                    output += f'{flash_color}██{Colors.RESET}'
                elif is_flashing:
                    flash_color = f'{Colors.BG_WHITE}{Colors.WHITE}' if self.flash_frames % 2 == 0 else f'{Colors.BG_GRAY}'
                    output += move_cursor(game_top + 1 + y, game_left + 1 + x * 2)
                    output += f'{flash_color}██{Colors.RESET}'
        
        # 绘制当前方块
        if self.state == GameState.PLAYING:
            shape = self.get_shape()
            piece_color = PIECE_COLORS[self.current_piece]
            for row in range(len(shape)):
                for col in range(len(shape[row])):
                    if shape[row][col]:
                        screen_y = game_top + 1 + self.piece_y + row
                        screen_x = game_left + 1 + (self.piece_x + col) * 2
                        if self.piece_y + row >= 0:
                            output += move_cursor(screen_y, screen_x)
                            output += f'{piece_color}██{Colors.RESET}'
            
            # 绘制幽灵方块
            ghost_y = self.piece_y
            while self.is_valid_position(self.piece_x, ghost_y + 1, self.current_rotation):
                ghost_y += 1
            if ghost_y != self.piece_y:
                for row in range(len(shape)):
                    for col in range(len(shape[row])):
                        if shape[row][col]:
                            screen_y = game_top + 1 + ghost_y + row
                            screen_x = game_left + 1 + (self.piece_x + col) * 2
                            if ghost_y + row >= 0:
                                output += move_cursor(screen_y, screen_x)
                                output += f'{Colors.DIM}{piece_color}░░{Colors.RESET}'
            
            # 绘制粒子
            for p in self.particles:
                px = round(game_left + 1 + p.x)
                py = round(game_top + 1 + p.y)
                if 0 < px < cols and 0 < py < rows:
                    output += move_cursor(py, px)
                    output += f'{p.color}{p.char}{Colors.RESET}'
            
            # 绘制连击消息
            if self.combo_frames > 0 and self.combo_message:
                msg_x = game_left + (self.board_width * 2 - len(self.combo_message)) // 2 + 1
                msg_y = game_top + self.board_height // 2
                pulse = self.combo_frames % 4 < 2
                msg_color = Colors.YELLOW if 'TETRIS' in self.combo_message else Colors.CYAN
                if not pulse:
                    msg_color = Colors.RED if 'TETRIS' in self.combo_message else Colors.WHITE
                output += move_cursor(msg_y, msg_x)
                output += f'{Colors.BOLD}{msg_color}{self.combo_message}{Colors.RESET}'
        
        # 绘制侧边面板
        panel_x = game_left + self.board_width * 2 + 4
        output += move_cursor(game_top, panel_x)
        output += f'{Colors.CYAN}┌──────────┐{Colors.RESET}'
        output += move_cursor(game_top + 1, panel_x)
        output += f'{Colors.CYAN}│ SCORE    │{Colors.RESET}'
        output += move_cursor(game_top + 2, panel_x)
        output += f'{Colors.CYAN}│ {str(self.score).rjust(8)} │{Colors.RESET}'
        output += move_cursor(game_top + 3, panel_x)
        output += f'{Colors.CYAN}├──────────┤{Colors.RESET}'
        output += move_cursor(game_top + 4, panel_x)
        output += f'{Colors.CYAN}│ LEVEL    │{Colors.RESET}'
        output += move_cursor(game_top + 5, panel_x)
        output += f'{Colors.CYAN}│ {str(self.level).rjust(8)} │{Colors.RESET}'
        output += move_cursor(game_top + 6, panel_x)
        output += f'{Colors.CYAN}├──────────┤{Colors.RESET}'
        output += move_cursor(game_top + 7, panel_x)
        output += f'{Colors.CYAN}│ LINES    │{Colors.RESET}'
        output += move_cursor(game_top + 8, panel_x)
        output += f'{Colors.CYAN}│ {str(self.lines).rjust(8)} │{Colors.RESET}'
        output += move_cursor(game_top + 9, panel_x)
        output += f'{Colors.CYAN}├──────────┤{Colors.RESET}'
        output += move_cursor(game_top + 10, panel_x)
        output += f'{Colors.CYAN}│ HIGH     │{Colors.RESET}'
        output += move_cursor(game_top + 11, panel_x)
        output += f'{Colors.CYAN}│ {str(self.high_score).rjust(8)} │{Colors.RESET}'
        output += move_cursor(game_top + 12, panel_x)
        output += f'{Colors.CYAN}└──────────┘{Colors.RESET}'
        
        # 下一个方块预览
        output += move_cursor(game_top + 14, panel_x)
        output += f'{Colors.CYAN}┌──────────┐{Colors.RESET}'
        output += move_cursor(game_top + 15, panel_x)
        output += f'{Colors.CYAN}│  NEXT    │{Colors.RESET}'
        for i in range(4):
            output += move_cursor(game_top + 16 + i, panel_x)
            output += f'{Colors.CYAN}│          │{Colors.RESET}'
        output += move_cursor(game_top + 20, panel_x)
        output += f'{Colors.CYAN}└──────────┘{Colors.RESET}'
        
        if self.state in [GameState.PLAYING, GameState.NOT_STARTED]:
            next_shape = TETROMINOES[self.next_piece][0]
            next_color = PIECE_COLORS[self.next_piece]
            offset_x = (4 - len(next_shape[0])) // 2
            offset_y = (2 - len(next_shape)) // 2
            for row in range(len(next_shape)):
                for col in range(len(next_shape[row])):
                    if next_shape[row][col]:
                        output += move_cursor(
                            game_top + 17 + offset_y + row,
                            panel_x + 2 + (offset_x + col) * 2
                        )
                        output += f'{next_color}██{Colors.RESET}'
        
        mode_label = f'M:S {max(0, 40 - self.lines):>3}' if self.game_mode == 'sprint' else 'M:MARATHON'
        output += move_cursor(game_top + 21, panel_x + (12 - len(mode_label)) // 2)
        output += f'{Colors.DIM}{Colors.CYAN}{mode_label}{Colors.RESET}'
        
        # 开始/暂停/结束画面
        if self.state == GameState.NOT_STARTED:
            start_msg = '[ PRESS ANY KEY ]'
            start_x = game_left + (self.board_width * 2 - len(start_msg)) // 2 + 1
            start_y = game_top + self.board_height // 2
            output += move_cursor(start_y, start_x)
            output += f'{Colors.BLINK}{Colors.CYAN}{start_msg}{Colors.RESET}'
            
            mode_y = start_y + 2
            marathon_label = '[1] MARATHON' if self.selected_mode == 'marathon' else ' 1  MARATHON'
            sprint_label = '[2] SPRINT 40L' if self.selected_mode == 'sprint' else ' 2  SPRINT 40L'
            mode_prompt = f'MODE: {marathon_label}  {sprint_label}'
            mode_x = (cols - len(mode_prompt)) // 2
            output += move_cursor(mode_y, mode_x)
            output += f'{Colors.BOLD}{Colors.CYAN}{mode_prompt}{Colors.RESET}'
            
            controls = '←→ MODE  ↓ MOVE  ↑ ROT  SPC DROP  ESC MENU'
            ctrl_x = (cols - len(controls)) // 2
            output += move_cursor(game_top + self.board_height + 2, ctrl_x)
            output += f'{Colors.DIM}{Colors.CYAN}{controls}{Colors.RESET}'
            
        elif self.state == GameState.PAUSED:
            pause_msg = '══ PAUSED ══'
            pause_x = game_left + (self.board_width * 2) // 2 + 1 - len(pause_msg) // 2
            pause_y = game_top + self.board_height // 2 - 3
            output += move_cursor(pause_y, pause_x)
            output += f'{Colors.BLINK}{Colors.CYAN}{pause_msg}{Colors.RESET}'
            
            menu_items = ['Resume', 'Restart', 'Quit', 'List Games', 'Next Game']
            for i, item in enumerate(menu_items):
                marker = '► ' if i == 0 else '  '
                output += move_cursor(pause_y + 2 + i, pause_x + 2)
                output += f'{Colors.CYAN}{marker}{item}{Colors.RESET}'
            
        elif self.state == GameState.GAME_OVER:
            over_msg = '══ YOU WIN ══' if self.state == GameState.VICTORY else '══ GAME OVER ══'
            over_x = game_left + (self.board_width * 2 - len(over_msg)) // 2 + 1
            over_y = game_top + self.board_height // 2 - 1
            over_color = Colors.GREEN if self.state == GameState.VICTORY else Colors.RED
            output += move_cursor(over_y, over_x)
            output += f'{Colors.BOLD}{over_color}{over_msg}{Colors.RESET}'
            
            final_score = f'SCORE: {self.score}'
            score_x = game_left + (self.board_width * 2 - len(final_score)) // 2 + 1
            output += move_cursor(over_y + 2, score_x)
            output += f'{Colors.CYAN}{final_score}{Colors.RESET}'
            
            restart = '[ R ] RESTART  [ Q ] QUIT'
            restart_x = game_left + (self.board_width * 2 - len(restart)) // 2 + 1
            output += move_cursor(over_y + 5, restart_x)
            output += f'{Colors.DIM}{Colors.CYAN}{restart}{Colors.RESET}'
        
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.NOT_STARTED:
            if key in ['1', 'a', 'left']:
                self.selected_mode = 'marathon'
            elif key in ['2', 'd', 'right']:
                self.selected_mode = 'sprint'
            elif key in ['tab', 'm']:
                self.selected_mode = 'sprint' if self.selected_mode == 'marathon' else 'marathon'
            else:
                self.game_mode = self.selected_mode
                self.init_game()
                self.state = GameState.PLAYING
            return
        
        if self.state == GameState.GAME_OVER or self.state == GameState.VICTORY:
            if key == 'r':
                self.init_game()
                self.state = GameState.PLAYING
            return
        
        if self.state == GameState.PAUSED:
            if key == 'escape':
                self.state = GameState.PLAYING
            elif key == 'r':
                self.init_game()
                self.state = GameState.PLAYING
            return
        
        if self.state != GameState.PLAYING:
            return
        
        if key == 'escape':
            self.state = GameState.PAUSED
        elif key in ['left', 'a']:
            self.move_left()
        elif key in ['right', 'd']:
            self.move_right()
        elif key in ['down', 's']:
            if self.move_down():
                self.score += 1
        elif key in ['up', 'w']:
            self.rotate()
        elif key == ' ':
            self.hard_drop()
        elif key == 'r':
            self.init_game()
            self.state = GameState.PLAYING


# ============================================================================
# 太空侵略者 (Space Invaders)
# ============================================================================

class SpaceInvadersGame(GameController):
    """太空侵略者游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.game_width = 50
        self.game_height = 20
        self.invader_rows = 4
        self.invader_cols = 8
        self.invader_spacing_x = 5
        self.invader_spacing_y = 2
        
        self.player_x = self.game_width / 2
        self.player_y = self.game_height - 1
        self.lives = 3
        
        self.invaders: List[Dict] = []
        self.invader_direction = 1
        self.invader_move_timer = 0
        self.invader_move_delay = 30
        
        self.bullets: List[Dict] = []
        self.player_shoot_cooldown = 0
        self.invader_shoot_timer = 0
        
        self.explosions: List[Dict] = []
        self.particles: List[Particle] = []
        self.score_popups: List[ScorePopup] = []
        
        self.shake_frames = 0
        self.shake_intensity = 0
        self.hit_flash_frames = 0
        self.kill_streak = 0
        self.kill_streak_timer = 0
        self.glitch_frame = 0
        
        self.invader_sprites = [
            ['<O>', '</\\\\>'],
            ['/V\\\\', '\\\\^/'],
            ['|=|', '|#|'],
        ]
        
    def init_game(self):
        """初始化游戏"""
        self.player_x = self.game_width / 2
        self.score = 0 if self.state != GameState.VICTORY else self.score
        self.lives = 3 if self.state != GameState.VICTORY else self.lives
        self.state = GameState.NOT_STARTED
        self.bullets = []
        self.explosions = []
        self.player_shoot_cooldown = 0
        self.invader_shoot_timer = 0
        self.invader_direction = 1
        self.invader_move_timer = 0
        self.particles = []
        self.score_popups = []
        self.shake_frames = 0
        self.kill_streak = 0
        self.kill_streak_timer = 0
        self.hit_flash_frames = 0
        self._init_invaders()
        
    def _init_invaders(self):
        """初始化侵略者"""
        self.invaders = []
        start_x = (self.game_width - self.invader_cols * self.invader_spacing_x) // 2
        start_y = 2
        
        for row in range(self.invader_rows):
            for col in range(self.invader_cols):
                self.invaders.append({
                    'x': start_x + col * self.invader_spacing_x,
                    'y': start_y + row * self.invader_spacing_y,
                    'alive': True,
                    'type': 2 if row == 0 else 1 if row == 1 else 0,
                })
                
    def spawn_particles(self, x: float, y: float, count: int, color: str, chars: List[str] = None):
        """生成粒子效果"""
        if chars is None:
            chars = ['✦', '★', '◆', '●']
        for i in range(count):
            angle = (math.pi * 2 * i) / count + random.random() * 0.5
            speed = 0.2 + random.random() * 0.4
            self.particles.append(Particle(
                x=x, y=y,
                char=random.choice(chars),
                color=color,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed * 0.5,
                life=10 + int(random.random() * 8)
            ))
            
    def add_score_popup(self, x: float, y: float, text: str, color: str = '\x1b[1;33m'):
        """添加分数弹出"""
        self.score_popups.append(ScorePopup(x=x, y=y, text=text, frames=18, color=color))
        
    def shoot_bullet(self, x: float, y: float, is_player: bool):
        """发射子弹"""
        self.bullets.append({'x': x, 'y': y, 'is_player': is_player})
        
    def update(self):
        """更新游戏状态"""
        if self.state not in [GameState.PLAYING]:
            return
            
        # 更新计时器
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.hit_flash_frames > 0:
            self.hit_flash_frames -= 1
        if self.kill_streak_timer > 0:
            self.kill_streak_timer -= 1
            if self.kill_streak_timer == 0:
                self.kill_streak = 0
                
        # 更新粒子
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.02
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)
                
        # 更新弹出文字
        for sp in self.score_popups[:]:
            sp.y -= 0.25
            sp.frames -= 1
            if sp.frames <= 0:
                self.score_popups.remove(sp)
                
        # 更新爆炸
        for exp in self.explosions[:]:
            exp['frame'] += 1
            if exp['frame'] >= 4:
                self.explosions.remove(exp)
                
        # 玩家射击冷却
        if self.player_shoot_cooldown > 0:
            self.player_shoot_cooldown -= 1
            
        # 侵略者射击
        self.invader_shoot_timer += 1
        alive_invaders = [i for i in self.invaders if i['alive']]
        if alive_invaders and self.invader_shoot_timer >= 60:
            self.invader_shoot_timer = 0
            shooter = random.choice(alive_invaders)
            self.shoot_bullet(shooter['x'] + 1, shooter['y'] + 1, False)
            
        # 移动侵略者
        self.invader_move_timer += 1
        invader_delay = max(10, 30 - (self.level - 1) * 4)
        if self.invader_move_timer >= invader_delay:
            self.invader_move_timer = 0
            
            hit_edge = False
            for inv in self.invaders:
                if not inv['alive']:
                    continue
                next_x = inv['x'] + self.invader_direction * 2
                if next_x <= 0 or next_x >= self.game_width - 3:
                    hit_edge = True
                    break
                    
            if hit_edge:
                self.invader_direction *= -1
            else:
                for inv in self.invaders:
                    if inv['alive']:
                        inv['x'] += self.invader_direction * 2
                    if inv['y'] >= self.player_y - 1:
                        self.state = GameState.GAME_OVER
                        if self.score > self.high_score:
                            self.high_score = self.score
                            
        # 移动子弹
        for bullet in self.bullets[:]:
            if bullet['is_player']:
                bullet['y'] -= 0.8
            else:
                bullet['y'] += 0.5
            if bullet['y'] < 0 or bullet['y'] >= self.game_height:
                self.bullets.remove(bullet)
                
        # 子弹碰撞检测
        for bullet in self.bullets[:]:
            if not bullet['is_player']:
                continue
            for inv in self.invaders:
                if not inv['alive']:
                    continue
                if (bullet['y'] >= inv['y'] and bullet['y'] <= inv['y'] + 1 and
                    bullet['x'] >= inv['x'] and bullet['x'] <= inv['x'] + 2):
                    inv['alive'] = False
                    bullet['y'] = -100
                    self.explosions.append({'x': inv['x'] + 1, 'y': inv['y'], 'frame': 0})
                    
                    self.kill_streak += 1
                    self.kill_streak_timer = 30
                    
                    base_score = (inv['type'] + 1) * 10
                    streak_bonus = self.kill_streak * 5 if self.kill_streak >= 3 else 0
                    total_score = base_score + streak_bonus
                    self.score += total_score
                    
                    self.shake_frames = 3 + min(self.kill_streak, 5)
                    self.shake_intensity = 1 + self.kill_streak // 3
                    
                    colors = [Colors.GREEN, Colors.YELLOW, Colors.MAGENTA]
                    self.spawn_particles(inv['x'] + 1, inv['y'], 
                                        6 + min(self.kill_streak, 6), 
                                        colors[inv['type']],
                                        ['✦', '★', '◆', '×'])
                    
                    popup_text = f'+{total_score}!' if self.kill_streak >= 3 else f'+{total_score}'
                    popup_color = Colors.RED if self.kill_streak >= 3 else Colors.YELLOW
                    self.add_score_popup(inv['x'] + 1, inv['y'] - 1, popup_text, popup_color)
                    break
                    
        # 子弹与玩家碰撞
        for bullet in self.bullets[:]:
            if bullet['is_player']:
                continue
            if (bullet['y'] >= self.player_y and bullet['y'] <= self.player_y + 1 and
                bullet['x'] >= self.player_x - 1 and bullet['x'] <= self.player_x + 1):
                bullet['y'] = -100
                self.explosions.append({'x': int(self.player_x), 'y': int(self.player_y), 'frame': 0})
                self.lives -= 1
                
                self.shake_frames = 12
                self.shake_intensity = 3
                self.hit_flash_frames = 15
                self.kill_streak = 0
                self.spawn_particles(int(self.player_x), int(self.player_y), 10, Colors.RED, ['✗', '☠', '×', '▒'])
                
                if self.lives <= 0:
                    self.state = GameState.GAME_OVER
                    if self.score > self.high_score:
                        self.high_score = self.score
                        
        # 检查胜利
        if all(not inv['alive'] for inv in self.invaders):
            self.state = GameState.VICTORY
            self.level += 1
            if self.score > self.high_score:
                self.high_score = self.score
                
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\x1b[2J\x1b[H'
        cols, rows = get_terminal_size()
        
        min_cols, min_rows = 40, 16
        if cols < min_cols or rows < min_rows:
            msg1 = 'Terminal too small!'
            msg2 = f'Need: {min_cols}×{min_rows}  Have: {cols}×{rows}'
            hint = 'Make pane larger'
            output += move_cursor(rows//2 - 1, max(1, cols//2 - len(msg1)//2))
            output += f'{Colors.CYAN}{msg1}{Colors.RESET}'
            output += move_cursor(rows//2 + 1, max(1, cols//2 - len(msg2)//2))
            output += f'{Colors.DIM}{msg2}{Colors.RESET}'
            return output
        
        game_left = max(2, (cols - self.game_width - 2) // 2)
        game_top = max(3, (rows - self.game_height - 4) // 2)
        
        render_left = game_left
        render_top = game_top
        if self.shake_frames > 0:
            render_left += int((random.random() - 0.5) * self.shake_intensity * 2)
            render_top += int((random.random() - 0.5) * self.shake_intensity)
        
        # 标题
        title = [
            '█ █ █▄█ █▀█ █▀▀ █▀█   █ █▄ █ █ █ ▄▀█ █▀▄ █▀▀ █▀█ █▀',
            '█▀█  █  █▀▀ ██▄ █▀▄   █ █ ▀█ ▀▄▀ █▀█ █▄▀ ██▄ █▀▄ ▄█',
        ]
        self.glitch_frame = (self.glitch_frame + 1) % 60
        glitch_offset = int((random.random() * 3) - 1) if self.glitch_frame >= 55 else 0
        title_x = (cols - len(title[0])) // 2 + glitch_offset
        
        if self.glitch_frame >= 55 and self.glitch_frame < 58:
            output += move_cursor(1, title_x)
            output += f'{Colors.RED}{title[0]}{Colors.RESET}'
            output += move_cursor(2, title_x + 1)
            output += f'{Colors.CYAN}{title[1]}{Colors.RESET}'
        else:
            output += move_cursor(1, title_x)
            output += f'{Colors.BOLD}{Colors.CYAN}{title[0]}{Colors.RESET}'
            output += move_cursor(2, title_x)
            output += f'{Colors.BOLD}{Colors.CYAN}{title[1]}{Colors.RESET}'
        
        # 状态栏
        lives_display = '♥' * self.lives
        stats = f'SCORE: {str(self.score).rjust(5, "0")}  LVL: {self.level}  {lives_display}'
        stats_x = (cols - len(stats)) // 2
        output += move_cursor(4, stats_x)
        output += f'{Colors.CYAN}{stats}{Colors.RESET}'
        
        # 边框
        border_color = Colors.RED if self.hit_flash_frames > 0 and self.hit_flash_frames % 4 < 2 else Colors.CYAN
        output += move_cursor(render_top, render_left)
        output += f'{border_color}╔{"═" * self.game_width}╗{Colors.RESET}'
        for y in range(self.game_height):
            output += move_cursor(render_top + 1 + y, render_left)
            output += f'{border_color}║{Colors.RESET}'
            output += move_cursor(render_top + 1 + y, render_left + self.game_width + 1)
            output += f'{border_color}║{Colors.RESET}'
        output += move_cursor(render_top + self.game_height + 1, render_left)
        output += f'{border_color}╚{"═" * self.game_width}╝{Colors.RESET}'
        
        if self.state == GameState.NOT_STARTED:
            start_msg = '[ PRESS ANY KEY TO PLAY ]'
            start_x = game_left + (self.game_width - len(start_msg)) // 2 + 1
            start_y = game_top + self.game_height // 2
            output += move_cursor(start_y, start_x)
            output += f'{Colors.BLINK}{Colors.CYAN}{start_msg}{Colors.RESET}'
            
            controls = '←→ MOVE  SPC FIRE  ESC MENU'
            ctrl_x = game_left + (self.game_width - len(controls)) // 2 + 1
            output += move_cursor(start_y + 2, ctrl_x)
            output += f'{Colors.DIM}{Colors.CYAN}{controls}{Colors.RESET}'
            
        elif self.state == GameState.PAUSED:
            pause_msg = '══ PAUSED ══'
            pause_x = game_left + self.game_width // 2 + 1 - len(pause_msg) // 2
            pause_y = game_top + self.game_height // 2 - 3
            output += move_cursor(pause_y, pause_x)
            output += f'{Colors.BLINK}{Colors.CYAN}{pause_msg}{Colors.RESET}'
            
        elif self.state in [GameState.GAME_OVER, GameState.VICTORY]:
            over_msg = '╔══ LEVEL COMPLETE! ══╗' if self.state == GameState.VICTORY else '╔══ GAME OVER ══╗'
            over_x = game_left + (self.game_width - len(over_msg)) // 2 + 1
            over_y = game_top + self.game_height // 2 - 1
            over_color = Colors.GREEN if self.state == GameState.VICTORY else Colors.RED
            output += move_cursor(over_y, over_x)
            output += f'{Colors.BOLD}{over_color}{over_msg}{Colors.RESET}'
            
            score_line = f'SCORE: {self.score}  HIGH: {self.high_score}'
            output += move_cursor(over_y + 1, game_left + (self.game_width - len(score_line)) // 2 + 1)
            output += f'{Colors.CYAN}{score_line}{Colors.RESET}'
            
            restart = '╚ [R] NEXT LEVEL  [Q] QUIT ╝' if self.state == GameState.VICTORY else '╚ [R] RESTART  [Q] QUIT ╝'
            output += move_cursor(over_y + 2, game_left + (self.game_width - len(restart)) // 2 + 1)
            output += f'{Colors.DIM}{Colors.CYAN}{restart}{Colors.RESET}'
            
        else:
            # 绘制侵略者
            anim_frame = self.glitch_frame // 15 % 2
            for inv in self.invaders:
                if not inv['alive']:
                    continue
                sprite = self.invader_sprites[inv['type']][anim_frame]
                colors = [Colors.GREEN, Colors.YELLOW, Colors.MAGENTA]
                output += move_cursor(render_top + 1 + int(inv['y']), render_left + 1 + int(inv['x']))
                output += f'{colors[inv["type"]]}{sprite}{Colors.RESET}'
                
            # 绘制子弹
            for bullet in self.bullets:
                sx = render_left + 1 + int(bullet['x'])
                sy = render_top + 1 + int(bullet['y'])
                if bullet['is_player']:
                    output += move_cursor(sy, sx)
                    output += f'{Colors.WHITE}│{Colors.RESET}'
                else:
                    output += move_cursor(sy, sx)
                    output += f'{Colors.RED}●{Colors.RESET}'
                    
            # 绘制爆炸
            for exp in self.explosions:
                sx = render_left + 1 + int(exp['x'])
                sy = render_top + 1 + int(exp['y'])
                exp_chars = ['*', '+', '×', '·']
                char = exp_chars[min(exp['frame'], 3)]
                output += move_cursor(sy, sx)
                output += f'{Colors.YELLOW}{char}{Colors.RESET}'
                
            # 绘制粒子
            for p in self.particles:
                sx = round(render_left + 1 + p.x)
                sy = round(render_top + 1 + p.y)
                if render_left < sx < render_left + self.game_width + 1 and render_top < sy < render_top + self.game_height + 1:
                    alpha = '' if p.life > 5 else Colors.DIM
                    output += move_cursor(sy, sx)
                    output += f'{alpha}{p.color}{p.char}{Colors.RESET}'
                    
            # 绘制弹出文字
            for sp in self.score_popups:
                sx = round(render_left + 1 + sp.x)
                sy = round(render_top + 1 + sp.y)
                if render_top < sy < render_top + self.game_height + 1:
                    alpha = Colors.BOLD if sp.frames > 10 else Colors.DIM
                    output += move_cursor(sy, sx)
                    output += f'{alpha}{sp.color}{sp.text}{Colors.RESET}'
                    
            # 绘制连击
            if self.kill_streak >= 3:
                streak_msg = f'★ {self.kill_streak}x KILL STREAK! ★' if self.kill_streak >= 5 else f'{self.kill_streak}x STREAK!'
                streak_x = render_left + (self.game_width - len(streak_msg)) // 2 + 1
                streak_color = Colors.RED if self.glitch_frame % 6 < 3 else Colors.YELLOW
                output += move_cursor(render_top + 2, streak_x)
                output += f'{Colors.BOLD}{streak_color}{streak_msg}{Colors.RESET}'
                
            # 绘制玩家
            player_sx = render_left + 1 + int(self.player_x) - 1
            player_sy = render_top + 1 + int(self.player_y)
            player_color = Colors.RED if self.hit_flash_frames > 0 and self.hit_flash_frames % 4 < 2 else Colors.CYAN
            output += move_cursor(player_sy, player_sx)
            output += f'{player_color}/█\\{Colors.RESET}'
        
        # 底部提示
        hint = f'HIGH: {self.high_score}  [ ESC ] MENU' if self.state == GameState.PLAYING else ''
        hint_x = (cols - len(hint)) // 2
        output += move_cursor(game_top + self.game_height + 3, hint_x)
        output += f'{Colors.DIM}{Colors.CYAN}{hint}{Colors.RESET}'
        
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.NOT_STARTED:
            self.state = GameState.PLAYING
            return
            
        if self.state in [GameState.GAME_OVER, GameState.VICTORY]:
            if key == 'r':
                if self.state == GameState.VICTORY:
                    self._init_invaders()
                else:
                    self.level = 1
                    self.init_game()
                self.state = GameState.PLAYING
            return
            
        if self.state == GameState.PAUSED:
            if key == 'escape':
                self.state = GameState.PLAYING
            elif key == 'r':
                self.level = 1
                self.init_game()
                self.state = GameState.PLAYING
            return
            
        if self.state != GameState.PLAYING:
            if key == 'escape':
                self.state = GameState.PAUSED
            return
        
        if key == 'escape':
            self.state = GameState.PAUSED
        elif key in ['left', 'a']:
            if self.player_x > 2:
                self.player_x -= 2
        elif key in ['right', 'd']:
            if self.player_x < self.game_width - 2:
                self.player_x += 2
        elif key == ' ':
            if self.player_shoot_cooldown == 0:
                self.shoot_bullet(self.player_x, self.player_y - 1, True)
                self.player_shoot_cooldown = 10


# ============================================================================
# 无尽跑酷 (Runner)
# ============================================================================

class RunnerGame(GameController):
    """无尽跑酷游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.game_width = 50
        self.game_height = 15
        self.player_x = 5
        self.player_y = self.game_height - 2
        self.obstacles: List[Dict] = []
        self.coins: List[Dict] = []
        self.particles: List[Particle] = []
        self.score_popups: List[ScorePopup] = []
        self.speed = 0.3
        self.distance = 0
        self.jump_velocity = 0
        self.is_jumping = False
        self.is_ducking = False
        self.ground_y = self.game_height - 1
        self.shake_frames = 0
        self.flash_frames = 0
        self.lives = 3
        self.invulnerable_frames = 0
        self.glitch_frame = 0
        
    def init_game(self):
        """初始化游戏"""
        self.player_y = self.ground_y
        self.jump_velocity = 0
        self.is_jumping = False
        self.is_ducking = False
        self.obstacles = []
        self.coins = []
        self.particles = []
        self.score_popups = []
        self.distance = 0
        self.score = 0
        self.lives = 3
        self.speed = 0.3
        self.state = GameState.NOT_STARTED
        self.shake_frames = 0
        self.flash_frames = 0
        self.invulnerable_frames = 0
        
    def spawn_obstacle(self):
        """生成障碍物"""
        obstacle_type = random.choice(['cactus', 'bird', 'rock'])
        if obstacle_type == 'cactus':
            self.obstacles.append({
                'x': self.game_width,
                'y': self.ground_y - 1,
                'type': 'cactus',
                'width': 2,
                'height': 2,
                'color': Colors.GREEN,
            })
        elif obstacle_type == 'bird' and self.distance > 500:
            self.obstacles.append({
                'x': self.game_width,
                'y': self.ground_y - 3 - random.randint(0, 1),
                'type': 'bird',
                'width': 3,
                'height': 1,
                'color': Colors.RED,
            })
        else:
            self.obstacles.append({
                'x': self.game_width,
                'y': self.ground_y,
                'type': 'rock',
                'width': 2,
                'height': 1,
                'color': Colors.DIM,
            })
            
    def spawn_coin(self):
        """生成金币"""
        coin_y = self.ground_y - 1 - random.randint(0, 2)
        self.coins.append({
            'x': self.game_width,
            'y': coin_y,
            'collected': False,
        })
        
    def spawn_particles(self, x: float, y: float, count: int, color: str):
        """生成粒子"""
        for i in range(count):
            angle = random.random() * math.pi * 2
            speed = random.random() * 0.5 + 0.2
            self.particles.append(Particle(
                x=x, y=y,
                char=random.choice(['✦', '★', '●']),
                color=color,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed * 0.5,
                life=8 + int(random.random() * 6)
            ))
            
    def update(self):
        """更新游戏状态"""
        if self.state not in [GameState.PLAYING]:
            return
            
        # 更新计时器
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.flash_frames > 0:
            self.flash_frames -= 1
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1
            
        # 重力
        if self.is_jumping:
            self.player_y += self.jump_velocity
            self.jump_velocity += 0.15
            if self.player_y >= self.ground_y:
                self.player_y = self.ground_y
                self.is_jumping = False
                self.jump_velocity = 0
                
        # 移动距离
        self.distance += self.speed * 10
        self.speed = min(0.8, 0.3 + self.distance / 2000)
        
        # 生成障碍物
        if random.random() < 0.02 + self.distance / 10000:
            if not self.obstacles or self.obstacles[-1]['x'] < self.game_width - 15:
                self.spawn_obstacle()
                
        # 生成金币
        if random.random() < 0.03:
            if not self.coins or self.coins[-1]['x'] < self.game_width - 8:
                self.spawn_coin()
                
        # 移动障碍物
        for obs in self.obstacles[:]:
            obs['x'] -= self.speed
            if obs['x'] + obs['width'] < 0:
                self.obstacles.remove(obs)
                self.score += 10
                
        # 移动金币
        for coin in self.coins[:]:
            coin['x'] -= self.speed
            if coin['x'] < 0:
                self.coins.remove(coin)
                
        # 收集金币
        for coin in self.coins[:]:
            if (abs(coin['x'] - self.player_x) < 2 and 
                abs(coin['y'] - self.player_y) < 2 and not coin['collected']):
                coin['collected'] = True
                self.score += 50
                self.spawn_particles(coin['x'], coin['y'], 5, Colors.YELLOW)
                self.score_popups.append(ScorePopup(
                    x=coin['x'], y=coin['y'] - 1,
                    text='+50', frames=15, color=Colors.YELLOW
                ))
                self.coins.remove(coin)
                
        # 碰撞检测
        if self.invulnerable_frames == 0:
            player_height = 1 if self.is_ducking else 2
            player_top = self.player_y - player_height + 1
            for obs in self.obstacles:
                if (obs['x'] < self.player_x + 1 and obs['x'] + obs['width'] > self.player_x - 1 and
                    obs['y'] >= player_top and obs['y'] <= self.player_y):
                    self.lives -= 1
                    self.invulnerable_frames = 60
                    self.shake_frames = 10
                    self.flash_frames = 8
                    self.spawn_particles(self.player_x, self.player_y, 10, Colors.RED)
                    if self.lives <= 0:
                        self.state = GameState.GAME_OVER
                        if self.score > self.high_score:
                            self.high_score = self.score
                            
        # 更新粒子
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.02
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)
                
        # 更新弹出文字
        for sp in self.score_popups[:]:
            sp.y -= 0.2
            sp.frames -= 1
            if sp.frames <= 0:
                self.score_popups.remove(sp)
                
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\\x1b[2J\\x1b[H'
        cols, rows = get_terminal_size()
        
        game_left = max(2, (cols - self.game_width - 2) // 2)
        game_top = max(3, (rows - self.game_height - 4) // 2)
        
        render_left = game_left
        render_top = game_top
        if self.shake_frames > 0:
            render_left += int((random.random() - 0.5) * 3)
            render_top += int((random.random() - 0.5) * 2)
            
        # 标题
        title = '══ 无尽跑酷 ══'
        title_x = (cols - len(title)) // 2
        output += move_cursor(1, title_x)
        output += f'{Colors.BOLD}{Colors.YELLOW}{title}{Colors.RESET}'
        
        # 状态栏
        stats = f'DIST: {int(self.distance):>5}  SCORE: {self.score:>5}  ♥{self.lives}'
        stats_x = (cols - len(stats)) // 2
        output += move_cursor(3, stats_x)
        output += f'{Colors.CYAN}{stats}{Colors.RESET}'
        
        # 边框
        output += move_cursor(render_top, render_left)
        output += f'{Colors.DIM}╔{"═" * self.game_width}╗{Colors.RESET}'
        for y in range(self.game_height):
            output += move_cursor(render_top + 1 + y, render_left)
            output += f'{Colors.DIM}║{Colors.RESET}'
            output += move_cursor(render_top + 1 + y, render_left + self.game_width + 1)
            output += f'{Colors.DIM}║{Colors.RESET}'
        output += move_cursor(render_top + self.game_height + 1, render_left)
        output += f'{Colors.DIM}╚{"═" * self.game_width}╝{Colors.RESET}'
        
        # 地面
        output += move_cursor(render_top + self.ground_y + 1, render_left + 1)
        output += f'{Colors.DIM}{"─" * self.game_width}{Colors.RESET}'
        
        if self.state == GameState.NOT_STARTED:
            start_msg = '[ 按任意键开始奔跑！]'
            start_x = game_left + (self.game_width - len(start_msg)) // 2
            start_y = game_top + self.game_height // 2
            output += move_cursor(start_y, start_x)
            output += f'{Colors.BLINK}{Colors.YELLOW}{start_msg}{Colors.RESET}'
            controls = '↑/空格 跳跃  ↓ 下蹲  ESC 菜单'
            ctrl_x = game_left + (self.game_width - len(controls)) // 2
            output += move_cursor(start_y + 2, ctrl_x)
            output += f'{Colors.DIM}{controls}{Colors.RESET}'
        elif self.state == GameState.PAUSED:
            pause_msg = '══ 暂停 ══'
            pause_x = game_left + self.game_width // 2 - len(pause_msg) // 2
            pause_y = game_top + self.game_height // 2
            output += move_cursor(pause_y, pause_x)
            output += f'{Colors.BLINK}{Colors.CYAN}{pause_msg}{Colors.RESET}'
        elif self.state == GameState.GAME_OVER:
            over_msg = '══ 游戏结束 ══'
            over_x = game_left + (self.game_width - len(over_msg)) // 2
            over_y = game_top + self.game_height // 2 - 1
            output += move_cursor(over_y, over_x)
            output += f'{Colors.BOLD}{Colors.RED}{over_msg}{Colors.RESET}'
            score_line = f'距离：{int(self.distance)}  得分：{self.score}'
            output += move_cursor(over_y + 1, game_left + (self.game_width - len(score_line)) // 2)
            output += f'{Colors.CYAN}{score_line}{Colors.RESET}'
            restart = '[R] 重来  [Q] 退出'
            output += move_cursor(over_y + 3, game_left + (self.game_width - len(restart)) // 2)
            output += f'{Colors.DIM}{restart}{Colors.RESET}'
        else:
            # 绘制玩家
            if self.invulnerable_frames == 0 or self.invulnerable_frames % 4 < 2:
                player_color = Colors.RED if self.flash_frames > 0 else Colors.CYAN
                if self.is_ducking:
                    player_char = '◙'
                elif self.is_jumping:
                    player_char = '▲'
                else:
                    player_char = '▓'
                output += move_cursor(render_top + self.player_y + 1, render_left + int(self.player_x) + 1)
                output += f'{player_color}{player_char}{Colors.RESET}'
                
            # 绘制障碍物
            for obs in self.obstacles:
                sx = render_left + 1 + int(obs['x'])
                sy = render_top + 1 + int(obs['y'])
                if obs['type'] == 'cactus':
                    char = '♣'
                elif obs['type'] == 'bird':
                    char = '♫'
                else:
                    char = '■'
                output += move_cursor(sy, sx)
                output += f'{obs["color"]}{char}{Colors.RESET}'
                
            # 绘制金币
            for coin in self.coins:
                if not coin['collected']:
                    sx = render_left + 1 + int(coin['x'])
                    sy = render_top + 1 + int(coin['y'])
                    blink = '●' if self.glitch_frame % 8 < 4 else '○'
                    output += move_cursor(sy, sx)
                    output += f'{Colors.YELLOW}{blink}{Colors.RESET}'
                    
            # 绘制粒子
            for p in self.particles:
                sx = round(render_left + 1 + p.x)
                sy = round(render_top + 1 + p.y)
                if 0 < sy < render_top + self.game_height + 1:
                    output += move_cursor(sy, sx)
                    output += f'{p.color}{p.char}{Colors.RESET}'
                    
            # 绘制弹出文字
            for sp in self.score_popups:
                sx = round(render_left + 1 + sp.x)
                sy = round(render_top + 1 + sp.y)
                if sy > render_top:
                    output += move_cursor(sy, sx)
                    output += f'{sp.color}{sp.text}{Colors.RESET}'
                    
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.NOT_STARTED:
            self.state = GameState.PLAYING
            return
            
        if self.state in [GameState.GAME_OVER]:
            if key == 'r':
                self.init_game()
                self.state = GameState.PLAYING
            return
            
        if self.state == GameState.PAUSED:
            if key == 'escape':
                self.state = GameState.PLAYING
            return
            
        if self.state != GameState.PLAYING:
            if key == 'escape':
                self.state = GameState.PAUSED
            return
            
        if key == 'escape':
            self.state = GameState.PAUSED
        elif key in ['up', 'w', ' '] and not self.is_jumping:
            self.is_jumping = True
            self.jump_velocity = -1.8
        elif key in ['down', 's']:
            self.is_ducking = True
        else:
            self.is_ducking = False


# ============================================================================
# 密码破解 (Crack)
# ============================================================================

class CrackGame(GameController):
    """密码破解游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.code_length = 4
        self.max_attempts = 10
        self.secret_code: List[int] = []
        self.current_guess: List[int] = []
        self.attempts: List[Dict] = []
        self.cursor_pos = 0
        self.difficulty = 1
        self.hints_used = 0
        self.time_left = 120
        self.timer_interval = 60
        self.timer_counter = 0
        self.glitch_frame = 0
        
    def init_game(self):
        """初始化游戏"""
        self.generate_code()
        self.current_guess = [0] * self.code_length
        self.attempts = []
        self.cursor_pos = 0
        self.hints_used = 0
        self.time_left = 120
        self.timer_counter = 0
        self.state = GameState.PLAYING
        self.score = 0
        
    def generate_code(self):
        """生成密码"""
        self.secret_code = [random.randint(0, 9) for _ in range(self.code_length)]
        
    def check_guess(self) -> Dict:
        """检查猜测"""
        bulls = sum(1 for i in range(self.code_length) if self.current_guess[i] == self.secret_code[i])
        cows = 0
        guess_copy = self.current_guess.copy()
        secret_copy = self.secret_code.copy()
        for i in range(self.code_length):
            if guess_copy[i] == secret_copy[i]:
                guess_copy[i] = -1
                secret_copy[i] = -1
        for i in range(self.code_length):
            if guess_copy[i] != -1 and guess_copy[i] in secret_copy:
                cows += 1
                secret_copy[secret_copy.index(guess_copy[i])] = -1
        return {'bulls': bulls, 'cows': cows, 'guess': self.current_guess.copy()}
        
    def update(self):
        """更新游戏状态"""
        if self.state != GameState.PLAYING:
            return
            
        self.timer_counter += 1
        if self.timer_counter >= self.timer_interval:
            self.timer_counter = 0
            self.time_left -= 1
            if self.time_left <= 0:
                self.state = GameState.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
                    
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\\x1b[2J\\x1b[H'
        cols, rows = get_terminal_size()
        
        game_width = 50
        game_left = max(2, (cols - game_width) // 2)
        game_top = max(2, (rows - 20) // 2)
        
        # 标题
        title = '══ 密码破解 ══'
        title_x = (cols - len(title)) // 2
        output += move_cursor(1, title_x)
        output += f'{Colors.BOLD}{Colors.MAGENTA}{title}{Colors.RESET}'
        
        # 状态栏
        time_color = Colors.GREEN if self.time_left > 30 else Colors.RED if self.time_left > 10 else Colors.DARK_RED
        stats = f'时间：{self.time_left}s  尝试：{len(self.attempts)}/{self.max_attempts}  提示：{self.hints_used}'
        stats_x = (cols - len(stats)) // 2
        output += move_cursor(3, stats_x)
        output += f'{time_color}{stats}{Colors.RESET}'
        
        # 密码显示框
        box_width = 30
        box_left = game_left + (game_width - box_width) // 2
        output += move_cursor(game_top, box_left)
        output += f'{Colors.MAGENTA}╔{"═" * box_width}╗{Colors.RESET}'
        
        # 当前猜测
        guess_display = ' '.join(str(d) if i != self.cursor_pos else f'[{d}]' for i, d in enumerate(self.current_guess))
        guess_text = f'猜测：{guess_display}'
        output += move_cursor(game_top + 2, box_left + 2)
        output += f'{Colors.CYAN}{guess_text}{Colors.RESET}'
        
        # 控制提示
        ctrl_text = '←→选择位  ↑↓改数字  ENTER确认  H提示  R重来'
        output += move_cursor(game_top + 4, box_left + 2)
        output += f'{Colors.DIM}{ctrl_text}{Colors.RESET}'
        
        # 历史尝试
        history_top = game_top + 6
        output += move_cursor(history_top, box_left)
        output += f'{Colors.MAGENTA}╠{"═" * box_width}╣{Colors.RESET}'
        
        for i, attempt in enumerate(self.attempts[-6:]):
            guess_str = ''.join(str(d) for d in attempt['guess'])
            result = f'●{attempt["bulls"]} ○{attempt["cows"]}'
            line = f'#{len(self.attempts) - 6 + i}: {guess_str} → {result}'
            color = Colors.GREEN if attempt['bulls'] == self.code_length else Colors.WHITE
            output += move_cursor(history_top + 1 + i, box_left + 2)
            output += f'{color}{line}{Colors.RESET}'
            
        output += move_cursor(history_top + 8, box_left)
        output += f'{Colors.MAGENTA}╚{"═" * box_width}╝{Colors.RESET}'
        
        # 游戏状态消息
        if self.state == GameState.GAME_OVER:
            over_msg = '══ 时间到！══'
            over_x = box_left + (box_width - len(over_msg)) // 2
            over_y = history_top + 10
            output += move_cursor(over_y, over_x)
            output += f'{Colors.BOLD}{Colors.RED}{over_msg}{Colors.RESET}'
            code_reveal = f'密码是：{"".join(str(d) for d in self.secret_code)}'
            output += move_cursor(over_y + 1, box_left + (box_width - len(code_reveal)) // 2)
            output += f'{Colors.YELLOW}{code_reveal}{Colors.RESET}'
            restart = '[R] 重来  [Q] 退出'
            output += move_cursor(over_y + 3, box_left + (box_width - len(restart)) // 2)
            output += f'{Colors.DIM}{restart}{Colors.RESET}'
        elif len(self.attempts) > 0 and self.attempts[-1]['bulls'] == self.code_length:
            win_msg = '══ 破解成功！══'
            win_x = box_left + (box_width - len(win_msg)) // 2
            win_y = history_top + 10
            output += move_cursor(win_y, win_x)
            output += f'{Colors.BOLD}{Colors.GREEN}{win_msg}{Colors.RESET}'
            bonus = self.time_left * 10
            self.score = 1000 + bonus
            score_text = f'得分：{self.score} (时间奖励：+{bonus})'
            output += move_cursor(win_y + 1, box_left + (box_width - len(score_text)) // 2)
            output += f'{Colors.YELLOW}{score_text}{Colors.RESET}'
            restart = '[R] 下一关  [Q] 退出'
            output += move_cursor(win_y + 3, box_left + (box_width - len(restart)) // 2)
            output += f'{Colors.DIM}{restart}{Colors.RESET}'
            
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.GAME_OVER or (len(self.attempts) > 0 and self.attempts[-1]['bulls'] == self.code_length):
            if key == 'r':
                self.init_game()
            return
            
        if self.state != GameState.PLAYING:
            return
            
        if key in ['left', 'a'] and self.cursor_pos > 0:
            self.cursor_pos -= 1
        elif key in ['right', 'd'] and self.cursor_pos < self.code_length - 1:
            self.cursor_pos += 1
        elif key in ['up', 'w']:
            self.current_guess[self.cursor_pos] = (self.current_guess[self.cursor_pos] + 1) % 10
        elif key in ['down', 's']:
            self.current_guess[self.cursor_pos] = (self.current_guess[self.cursor_pos] - 1) % 10
        elif key == 'enter':
            result = self.check_guess()
            self.attempts.append(result)
            if result['bulls'] == self.code_length:
                self.score = 1000 + self.time_left * 10
                if self.score > self.high_score:
                    self.high_score = self.score
            elif len(self.attempts) >= self.max_attempts:
                self.state = GameState.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
            else:
                self.current_guess = [0] * self.code_length
                self.cursor_pos = 0
        elif key == 'h' and self.hints_used < 3:
            # 显示一个正确位置的数字
            correct_positions = [i for i in range(self.code_length) if self.current_guess[i] == self.secret_code[i]]
            wrong_positions = [i for i in range(self.code_length) if i not in correct_positions]
            if wrong_positions:
                hint_pos = random.choice(wrong_positions)
                self.current_guess[hint_pos] = self.secret_code[hint_pos]
                self.hints_used += 1
                self.score = max(0, self.score - 100)


# ============================================================================
# 直升机 (Chopper)
# ============================================================================

class ChopperGame(GameController):
    """直升机游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.game_width = 50
        self.game_height = 18
        self.heli_x = 8
        self.heli_y = self.game_height // 2
        self.velocity = 0
        self.gravity = 0.08
        self.thrust = -0.15
        self.obstacles: List[Dict] = []
        self.fuel = 100
        self.fuel_consumption = 0.15
        self.scroll_speed = 0.4
        self.distance = 0
        self.level = 1
        self.particles: List[Particle] = []
        self.shake_frames = 0
        self.flash_frames = 0
        self.glitch_frame = 0
        self.rescue_target: Optional[Dict] = None
        self.has_rescued = False
        
    def init_game(self):
        """初始化游戏"""
        self.heli_y = self.game_height // 2
        self.velocity = 0
        self.fuel = 100
        self.obstacles = []
        self.particles = []
        self.distance = 0
        self.score = 0
        self.state = GameState.NOT_STARTED
        self.shake_frames = 0
        self.flash_frames = 0
        self.has_rescued = False
        self.rescue_target = None
        self._generate_initial_obstacles()
        
    def _generate_initial_obstacles(self):
        """生成初始障碍"""
        self.obstacles = []
        for x in range(self.game_width, self.game_width * 3, 15):
            gap_y = random.randint(4, self.game_height - 6)
            gap_size = random.randint(4, 7)
            self.obstacles.append({
                'x': x,
                'gap_y': gap_y,
                'gap_size': gap_size,
                'type': 'wall',
                'passed': False,
            })
            
    def spawn_fuel(self):
        """生成燃料包"""
        self.obstacles.append({
            'x': self.game_width + 10,
            'y': random.randint(3, self.game_height - 4),
            'type': 'fuel',
            'collected': False,
        })
        
    def spawn_rescue(self):
        """生成救援目标"""
        self.rescue_target = {
            'x': self.game_width + 20,
            'y': random.randint(5, self.game_height - 5),
            'rescued': False,
        }
        
    def spawn_particles(self, x: float, y: float, count: int, color: str):
        """生成粒子"""
        for i in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                char=random.choice(['✦', '●', '▒']),
                color=color,
                vx=(random.random() - 0.5) * 0.5,
                vy=(random.random() - 0.5) * 0.5,
                life=6 + int(random.random() * 4)
            ))
            
    def update(self):
        """更新游戏状态"""
        if self.state not in [GameState.PLAYING]:
            return
            
        # 物理
        self.velocity += self.gravity
        self.heli_y += self.velocity
        
        # 边界检查
        if self.heli_y <= 1:
            self.heli_y = 1
            self.velocity = 0
        if self.heli_y >= self.game_height - 2:
            self.heli_y = self.game_height - 2
            self.velocity = 0
            
        # 燃料消耗
        self.fuel -= self.fuel_consumption
        if self.fuel <= 0:
            self.fuel = 0
            self.state = GameState.GAME_OVER
            
        # 滚动
        self.distance += self.scroll_speed
        self.scroll_speed = min(0.8, 0.4 + self.distance / 500)
        
        # 移动障碍
        for obs in self.obstacles[:]:
            obs['x'] -= self.scroll_speed
            if obs['type'] == 'wall' and not obs['passed'] and obs['x'] + 3 < self.heli_x:
                obs['passed'] = True
                self.score += 50
            if obs['type'] == 'fuel' and obs['x'] < -2:
                self.obstacles.remove(obs)
                
        # 移动救援目标
        if self.rescue_target:
            self.rescue_target['x'] -= self.scroll_speed
            if self.rescue_target['x'] < -2:
                self.rescue_target = None
                
        # 生成新障碍
        if self.obstacles and self.obstacles[-1]['x'] < self.game_width - 20:
            gap_y = random.randint(4, self.game_height - 6)
            gap_size = max(3, 7 - int(self.distance / 200))
            self.obstacles.append({
                'x': self.game_width + random.randint(0, 10),
                'gap_y': gap_y,
                'gap_size': gap_size,
                'type': 'wall',
                'passed': False,
            })
            if random.random() < 0.3:
                self.spawn_fuel()
                
        # 生成救援任务
        if not self.rescue_target and self.distance > 300 and not self.has_rescued:
            if random.random() < 0.02:
                self.spawn_rescue()
                
        # 收集燃料
        for obs in self.obstacles[:]:
            if obs['type'] == 'fuel' and not obs['collected']:
                if abs(obs['x'] - self.heli_x) < 3 and abs(obs['y'] - self.heli_y) < 2:
                    obs['collected'] = True
                    self.fuel = min(100, self.fuel + 30)
                    self.score += 25
                    self.spawn_particles(obs['x'], obs['y'], 5, Colors.GREEN)
                    self.obstacles.remove(obs)
                    
        # 救援
        if self.rescue_target and not self.rescue_target['rescued']:
            if (abs(self.rescue_target['x'] - self.heli_x) < 3 and 
                abs(self.rescue_target['y'] - self.heli_y) < 2):
                self.rescue_target['rescued'] = True
                self.has_rescued = True
                self.score += 200
                self.fuel = min(100, self.fuel + 20)
                self.spawn_particles(self.heli_x, self.heli_y, 15, Colors.YELLOW)
                self.rescue_target = None
                
        # 碰撞检测
        for obs in self.obstacles:
            if obs['type'] == 'wall':
                if self.heli_x + 2 > obs['x'] and self.heli_x - 2 < obs['x'] + 3:
                    if self.heli_y < obs['gap_y'] or self.heli_y > obs['gap_y'] + obs['gap_size']:
                        self.state = GameState.GAME_OVER
                        self.shake_frames = 15
                        self.spawn_particles(self.heli_x, self.heli_y, 20, Colors.RED)
                        
        # 更新粒子
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)
                
        # 更新计时器
        if self.shake_frames > 0:
            self.shake_frames -= 1
            
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\\x1b[2J\\x1b[H'
        cols, rows = get_terminal_size()
        
        game_left = max(2, (cols - self.game_width - 2) // 2)
        game_top = max(2, (rows - self.game_height - 4) // 2)
        
        render_left = game_left
        render_top = game_top
        if self.shake_frames > 0:
            render_left += int((random.random() - 0.5) * 4)
            render_top += int((random.random() - 0.5) * 2)
            
        # 标题
        title = '══ 直升机 ══'
        title_x = (cols - len(title)) // 2
        output += move_cursor(1, title_x)
        output += f'{Colors.BOLD}{Colors.CYAN}{title}{Colors.RESET}'
        
        # 状态栏
        fuel_bar = '█' * int(self.fuel / 5) + '░' * (20 - int(self.fuel / 5))
        fuel_color = Colors.GREEN if self.fuel > 50 else Colors.YELLOW if self.fuel > 25 else Colors.RED
        stats = f'距离：{int(self.distance):>5}  得分：{self.score:>5}  燃料：{fuel_color}{fuel_bar}{Colors.RESET}'
        output += move_cursor(3, (cols - len(stats)) // 2)
        output += f'{stats}{Colors.RESET}'
        
        # 边框
        output += move_cursor(render_top, render_left)
        output += f'{Colors.DIM}╔{"═" * self.game_width}╗{Colors.RESET}'
        for y in range(self.game_height):
            output += move_cursor(render_top + 1 + y, render_left)
            output += f'{Colors.DIM}║{Colors.RESET}'
            output += move_cursor(render_top + 1 + y, render_left + self.game_width + 1)
            output += f'{Colors.DIM}║{Colors.RESET}'
        output += move_cursor(render_top + self.game_height + 1, render_left)
        output += f'{Colors.DIM}╚{"═" * self.game_width}╝{Colors.RESET}'
        
        if self.state == GameState.NOT_STARTED:
            start_msg = '[ 按住空格起飞 ]'
            start_x = game_left + (self.game_width - len(start_msg)) // 2
            start_y = game_top + self.game_height // 2
            output += move_cursor(start_y, start_x)
            output += f'{Colors.BLINK}{Colors.CYAN}{start_msg}{Colors.RESET}'
            controls = '空格/↑上升  ↓下降  ESC 菜单'
            output += move_cursor(start_y + 2, game_left + (self.game_width - len(controls)) // 2)
            output += f'{Colors.DIM}{controls}{Colors.RESET}'
        elif self.state == GameState.PAUSED:
            pause_msg = '══ 暂停 ══'
            output += move_cursor(render_top + self.game_height // 2, render_left + self.game_width // 2 - len(pause_msg) // 2)
            output += f'{Colors.BLINK}{Colors.CYAN}{pause_msg}{Colors.RESET}'
        elif self.state == GameState.GAME_OVER:
            over_msg = '══ 坠毁！══'
            over_x = game_left + (self.game_width - len(over_msg)) // 2
            over_y = game_top + self.game_height // 2 - 1
            output += move_cursor(over_y, over_x)
            output += f'{Colors.BOLD}{Colors.RED}{over_msg}{Colors.RESET}'
            score_text = f'最终得分：{self.score}  距离：{int(self.distance)}'
            output += move_cursor(over_y + 1, game_left + (self.game_width - len(score_text)) // 2)
            output += f'{Colors.CYAN}{score_text}{Colors.RESET}'
            restart = '[R] 重来  [Q] 退出'
            output += move_cursor(over_y + 3, game_left + (self.game_width - len(restart)) // 2)
            output += f'{Colors.DIM}{restart}{Colors.RESET}'
        else:
            # 绘制直升机
            heli_chars = ['≋', '≈']
            heli_char = heli_chars[self.glitch_frame // 8 % 2]
            output += move_cursor(render_top + int(self.heli_y) + 1, render_left + int(self.heli_x) + 1)
            output += f'{Colors.YELLOW}{heli_char}{Colors.RESET}'
            
            # 绘制尾焰
            if self.velocity < 0:
                flame_len = int(abs(self.velocity) * 3) + 1
                for i in range(flame_len):
                    flame_char = '·' if i % 2 == 0 else ','
                    flame_color = Colors.YELLOW if i == 0 else Colors.RED
                    output += move_cursor(render_top + int(self.heli_y) + 1, render_left + int(self.heli_x) - i)
                    output += f'{flame_color}{flame_char}{Colors.RESET}'
                    
            # 绘制障碍墙
            for obs in self.obstacles:
                if obs['type'] == 'wall':
                    for y in range(self.game_height):
                        if y < obs['gap_y'] or y > obs['gap_y'] + obs['gap_size']:
                            sx = render_left + 1 + int(obs['x'])
                            sy = render_top + 1 + y
                            if 0 <= sy - render_top - 1 < self.game_height:
                                output += move_cursor(sy, sx)
                                output += f'{Colors.DIM}██{Colors.RESET}'
                                
            # 绘制燃料包
            for obs in self.obstacles:
                if obs['type'] == 'fuel' and not obs['collected']:
                    sx = render_left + 1 + int(obs['x'])
                    sy = render_top + 1 + int(obs['y'])
                    blink = 'F' if self.glitch_frame % 6 < 3 else 'f'
                    output += move_cursor(sy, sx)
                    output += f'{Colors.GREEN}{blink}{Colors.RESET}'
                    
            # 绘制救援目标
            if self.rescue_target and not self.rescue_target['rescued']:
                sx = render_left + 1 + int(self.rescue_target['x'])
                sy = render_top + 1 + int(self.rescue_target['y'])
                blink = '♥' if self.glitch_frame % 8 < 4 else '♡'
                output += move_cursor(sy, sx)
                output += f'{Colors.MAGENTA}{blink}{Colors.RESET}'
                
            # 绘制粒子
            for p in self.particles:
                sx = round(render_left + 1 + p.x)
                sy = round(render_top + 1 + p.y)
                if render_top < sy < render_top + self.game_height + 1:
                    output += move_cursor(sy, sx)
                    output += f'{p.color}{p.char}{Colors.RESET}'
                    
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.NOT_STARTED:
            if key == ' ':
                self.state = GameState.PLAYING
            return
            
        if self.state in [GameState.GAME_OVER]:
            if key == 'r':
                self.init_game()
                self.state = GameState.PLAYING
            return
            
        if self.state == GameState.PAUSED:
            if key == 'escape':
                self.state = GameState.PLAYING
            return
            
        if self.state != GameState.PLAYING:
            if key == 'escape':
                self.state = GameState.PAUSED
            return
            
        if key == 'escape':
            self.state = GameState.PAUSED
        elif key in [' ', 'up', 'w']:
            self.velocity += self.thrust
            self.fuel = max(0, self.fuel - 0.3)
        elif key in ['down', 's']:
            self.velocity += 0.05


# ============================================================================
# 打砖块 (Breakout)
# ============================================================================

class BreakoutGame(GameController):
    """打砖块游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.game_width = 40
        self.game_height = 20
        self.paddle_width = 8
        self.paddle_x = (self.game_width - self.paddle_width) // 2
        self.paddle_y = self.game_height - 2
        self.ball_x = self.game_width / 2
        self.ball_y = self.game_height - 4
        self.ball_dx = 0.3
        self.ball_dy = -0.3
        self.bricks: List[Dict] = []
        self.particles: List[Particle] = []
        self.score_popups: List[ScorePopup] = []
        self.lives = 3
        self.level = 1
        self.shake_frames = 0
        self.flash_frames = 0
        self.combo = 0
        self.combo_timer = 0
        self.glitch_frame = 0
        
    def init_game(self):
        """初始化游戏"""
        self.paddle_x = (self.game_width - self.paddle_width) // 2
        self.reset_ball()
        self.lives = 3
        self.score = 0
        self.combo = 0
        self.combo_timer = 0
        self.state = GameState.NOT_STARTED
        self.particles = []
        self.score_popups = []
        self.shake_frames = 0
        self._create_bricks()
        
    def reset_ball(self):
        """重置球"""
        self.ball_x = self.paddle_x + self.paddle_width / 2
        self.ball_y = self.paddle_y - 1
        self.ball_dx = random.choice([-0.25, 0.25])
        self.ball_dy = -0.3
        
    def _create_bricks(self):
        """创建砖块"""
        self.bricks = []
        rows = min(5, 3 + self.level)
        colors = [Colors.RED, Colors.YELLOW, Colors.GREEN, Colors.CYAN, Colors.MAGENTA]
        for row in range(rows):
            for col in range(self.game_width // 3):
                self.bricks.append({
                    'x': col * 3,
                    'y': row + 2,
                    'alive': True,
                    'color': colors[row % len(colors)],
                    'value': (rows - row) * 10,
                })
                
    def spawn_particles(self, x: float, y: float, count: int, color: str):
        """生成粒子"""
        for i in range(count):
            angle = random.random() * math.pi * 2
            speed = random.random() * 0.4 + 0.1
            self.particles.append(Particle(
                x=x, y=y,
                char=random.choice(['✦', '●', '▒', '░']),
                color=color,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=8 + int(random.random() * 6)
            ))
            
    def update(self):
        """更新游戏状态"""
        if self.state not in [GameState.PLAYING]:
            return
            
        # 更新计时器
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.flash_frames > 0:
            self.flash_frames -= 1
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0
                
        # 移动球
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        # 墙壁碰撞
        if self.ball_x <= 1 or self.ball_x >= self.game_width - 2:
            self.ball_dx *= -1
            self.ball_x = max(1, min(self.game_width - 2, self.ball_x))
        if self.ball_y <= 1:
            self.ball_dy *= -1
            self.ball_y = 1
            
        # 掉落
        if self.ball_y > self.game_height - 1:
            self.lives -= 1
            self.shake_frames = 8
            self.spawn_particles(self.ball_x, self.ball_y, 10, Colors.RED)
            if self.lives <= 0:
                self.state = GameState.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
            else:
                self.reset_ball()
                
        # 挡板碰撞
        paddle_top = self.paddle_y
        if (self.ball_y >= paddle_top and self.ball_y <= paddle_top + 1 and
            self.ball_x >= self.paddle_x and self.ball_x <= self.paddle_x + self.paddle_width):
            self.ball_dy = -abs(self.ball_dy)
            hit_pos = (self.ball_x - self.paddle_x) / self.paddle_width
            self.ball_dx = (hit_pos - 0.5) * 0.6
            self.ball_y = paddle_top - 0.1
            
        # 砖块碰撞
        for brick in self.bricks[:]:
            if not brick['alive']:
                continue
            if (self.ball_x >= brick['x'] and self.ball_x <= brick['x'] + 3 and
                self.ball_y >= brick['y'] and self.ball_y <= brick['y'] + 1):
                brick['alive'] = False
                self.combo += 1
                self.combo_timer = 30
                base_score = brick['value']
                combo_bonus = self.combo * 5 if self.combo >= 3 else 0
                total = base_score + combo_bonus
                self.score += total
                self.ball_dy *= -1
                self.shake_frames = 2
                self.spawn_particles(self.ball_x, self.ball_y, 6, brick['color'])
                if combo_bonus > 0:
                    self.score_popups.append(ScorePopup(
                        x=self.ball_x, y=self.ball_y - 1,
                        text=f'+{total}!', frames=15, color=Colors.RED
                    ))
                break
                
        # 更新粒子
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.01
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)
                
        # 更新弹出文字
        for sp in self.score_popups[:]:
            sp.y -= 0.2
            sp.frames -= 1
            if sp.frames <= 0:
                self.score_popups.remove(sp)
                
        # 检查胜利
        if all(not b['alive'] for b in self.bricks):
            self.state = GameState.VICTORY
            self.level += 1
            
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\\x1b[2J\\x1b[H'
        cols, rows = get_terminal_size()
        
        game_left = max(2, (cols - self.game_width - 2) // 2)
        game_top = max(2, (rows - self.game_height - 4) // 2)
        
        render_left = game_left
        render_top = game_top
        if self.shake_frames > 0:
            render_left += int((random.random() - 0.5) * 3)
            render_top += int((random.random() - 0.5) * 2)
            
        # 标题
        title = '══ 打砖块 ══'
        title_x = (cols - len(title)) // 2
        output += move_cursor(1, title_x)
        output += f'{Colors.BOLD}{Colors.YELLOW}{title}{Colors.RESET}'
        
        # 状态栏
        lives_display = '♥' * self.lives
        stats = f'关卡：{self.level}  得分：{self.score}  {lives_display}'
        output += move_cursor(3, (cols - len(stats)) // 2)
        output += f'{Colors.CYAN}{stats}{Colors.RESET}'
        
        # 边框
        output += move_cursor(render_top, render_left)
        output += f'{Colors.DIM}╔{"═" * self.game_width}╗{Colors.RESET}'
        for y in range(self.game_height):
            output += move_cursor(render_top + 1 + y, render_left)
            output += f'{Colors.DIM}║{Colors.RESET}'
            output += move_cursor(render_top + 1 + y, render_left + self.game_width + 1)
            output += f'{Colors.DIM}║{Colors.RESET}'
        output += move_cursor(render_top + self.game_height + 1, render_left)
        output += f'{Colors.DIM}╚{"═" * self.game_width}╝{Colors.RESET}'
        
        if self.state == GameState.NOT_STARTED:
            start_msg = '[ 按任意键发球 ]'
            start_x = game_left + (self.game_width - len(start_msg)) // 2
            start_y = game_top + self.game_height // 2
            output += move_cursor(start_y, start_x)
            output += f'{Colors.BLINK}{Colors.YELLOW}{start_msg}{Colors.RESET}'
            controls = '←→移动  空格发球  ESC 菜单'
            output += move_cursor(start_y + 2, game_left + (self.game_width - len(controls)) // 2)
            output += f'{Colors.DIM}{controls}{Colors.RESET}'
        elif self.state == GameState.PAUSED:
            pause_msg = '══ 暂停 ══'
            output += move_cursor(render_top + self.game_height // 2, render_left + self.game_width // 2 - len(pause_msg) // 2)
            output += f'{Colors.BLINK}{Colors.CYAN}{pause_msg}{Colors.RESET}'
        elif self.state in [GameState.GAME_OVER, GameState.VICTORY]:
            msg = '══ 通关！══' if self.state == GameState.VICTORY else '══ 游戏结束 ══'
            color = Colors.GREEN if self.state == GameState.VICTORY else Colors.RED
            output += move_cursor(render_top + self.game_height // 2 - 1, render_left + self.game_width // 2 - len(msg) // 2)
            output += f'{Colors.BOLD}{color}{msg}{Colors.RESET}'
            score_text = f'得分：{self.score}'
            output += move_cursor(render_top + self.game_height // 2, render_left + self.game_width // 2 - len(score_text) // 2)
            output += f'{Colors.CYAN}{score_text}{Colors.RESET}'
            restart = '[R] 继续  [Q] 退出'
            output += move_cursor(render_top + self.game_height // 2 + 2, render_left + self.game_width // 2 - len(restart) // 2)
            output += f'{Colors.DIM}{restart}{Colors.RESET}'
        else:
            # 绘制砖块
            for brick in self.bricks:
                if brick['alive']:
                    sx = render_left + 1 + int(brick['x'])
                    sy = render_top + 1 + int(brick['y'])
                    output += move_cursor(sy, sx)
                    output += f'{brick["color"]}███{Colors.RESET}'
                    
            # 绘制挡板
            paddle_char = '▀' * self.paddle_width
            output += move_cursor(render_top + self.paddle_y + 1, render_left + 1 + int(self.paddle_x))
            output += f'{Colors.CYAN}{paddle_char}{Colors.RESET}'
            
            # 绘制球
            ball_char = '●' if self.glitch_frame % 4 < 2 else '○'
            output += move_cursor(render_top + int(self.ball_y) + 1, render_left + int(self.ball_x) + 1)
            output += f'{Colors.WHITE}{ball_char}{Colors.RESET}'
            
            # 绘制连击
            if self.combo >= 3:
                combo_msg = f'{self.combo}x COMBO!'
                output += move_cursor(render_top + 2, render_left + (self.game_width - len(combo_msg)) // 2)
                output += f'{Colors.BOLD}{Colors.RED}{combo_msg}{Colors.RESET}'
                
            # 绘制粒子
            for p in self.particles:
                sx = round(render_left + 1 + p.x)
                sy = round(render_top + 1 + p.y)
                if render_top < sy < render_top + self.game_height + 1:
                    output += move_cursor(sy, sx)
                    output += f'{p.color}{p.char}{Colors.RESET}'
                    
            # 绘制弹出文字
            for sp in self.score_popups:
                sx = round(render_left + 1 + sp.x)
                sy = round(render_top + 1 + sp.y)
                if sy > render_top:
                    output += move_cursor(sy, sx)
                    output += f'{sp.color}{sp.text}{Colors.RESET}'
                    
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.NOT_STARTED:
            self.state = GameState.PLAYING
            return
            
        if self.state in [GameState.GAME_OVER, GameState.VICTORY]:
            if key == 'r':
                if self.state == GameState.VICTORY:
                    self._create_bricks()
                    self.reset_ball()
                else:
                    self.level = 1
                    self.init_game()
                self.state = GameState.PLAYING
            return
            
        if self.state == GameState.PAUSED:
            if key == 'escape':
                self.state = GameState.PLAYING
            return
            
        if self.state != GameState.PLAYING:
            if key == 'escape':
                self.state = GameState.PAUSED
            return
            
        if key == 'escape':
            self.state = GameState.PAUSED
        elif key in ['left', 'a']:
            self.paddle_x = max(0, self.paddle_x - 3)
        elif key in ['right', 'd']:
            self.paddle_x = min(self.game_width - self.paddle_width, self.paddle_x + 3)


# ============================================================================
# 高塔堆叠 (Tower)
# ============================================================================

class TowerGame(GameController):
    """高塔堆叠游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.game_width = 30
        self.game_height = 20
        self.base_width = 20
        self.block_height = 1
        self.blocks: List[Dict] = []
        self.current_block: Optional[Dict] = None
        self.direction = 1
        self.speed = 0.3
        self.missed = 0
        self.max_missed = 3
        self.particles: List[Particle] = []
        self.score_popups: List[ScorePopup] = []
        self.shake_frames = 0
        self.flash_frames = 0
        self.glitch_frame = 0
        self.perfect_streak = 0
        
    def init_game(self):
        """初始化游戏"""
        self.blocks = [{
            'x': (self.game_width - self.base_width) // 2,
            'y': self.game_height - 1,
            'width': self.base_width,
            'color': Colors.CYAN,
            'perfect': False,
        }]
        self.current_block = None
        self.direction = 1
        self.speed = 0.2
        self.missed = 0
        self.score = 0
        self.perfect_streak = 0
        self.state = GameState.NOT_STARTED
        self.particles = []
        self.score_popups = []
        self._spawn_block()
        
    def _spawn_block(self):
        """生成新方块"""
        if not self.blocks:
            return
        prev = self.blocks[-1]
        colors = [Colors.RED, Colors.YELLOW, Colors.GREEN, Colors.MAGENTA, Colors.BLUE]
        self.current_block = {
            'x': 0 if self.direction > 0 else self.game_width - prev['width'],
            'y': prev['y'] - 1,
            'width': prev['width'],
            'color': colors[len(self.blocks) % len(colors)],
            'moving': True,
        }
        self.speed = min(0.8, 0.2 + len(self.blocks) * 0.05)
        
    def place_block(self):
        """放置方块"""
        if not self.current_block or not self.blocks:
            return
            
        prev = self.blocks[-1]
        curr = self.current_block
        
        overlap_start = max(curr['x'], prev['x'])
        overlap_end = min(curr['x'] + curr['width'], prev['x'] + prev['width'])
        overlap = overlap_end - overlap_start
        
        if overlap <= 0:
            self.missed += 1
            self.spawn_particles(curr['x'] + curr['width']/2, curr['y'], 10, Colors.RED)
            if self.missed >= self.max_missed:
                self.state = GameState.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
            else:
                self._spawn_block()
            return
            
        # 计算完美度
        tolerance = 2
        is_perfect = abs(overlap - prev['width']) < tolerance
        
        if is_perfect:
            self.perfect_streak += 1
            new_width = prev['width']
            new_x = prev['x']
            bonus = 50 + self.perfect_streak * 10
            self.spawn_particles(curr['x'] + curr['width']/2, curr['y'], 15, Colors.YELLOW)
            self.score_popups.append(ScorePopup(
                x=curr['x'] + curr['width']/2, y=curr['y'] - 1,
                text='PERFECT!', frames=20, color=Colors.YELLOW
            ))
        else:
            self.perfect_streak = 0
            new_width = overlap
            new_x = overlap_start
            bonus = overlap
            self.spawn_particles(curr['x'] + curr['width']/2, curr['y'], 5, curr['color'])
            
        self.blocks.append({
            'x': new_x,
            'y': curr['y'],
            'width': new_width,
            'color': curr['color'],
            'perfect': is_perfect,
        })
        
        self.score += int(bonus)
        self.shake_frames = 3 if is_perfect else 1
        self._spawn_block()
        
    def spawn_particles(self, x: float, y: float, count: int, color: str):
        """生成粒子"""
        for i in range(count):
            angle = random.random() * math.pi * 2
            speed = random.random() * 0.3 + 0.1
            self.particles.append(Particle(
                x=x, y=y,
                char=random.choice(['✦', '●', '▒']),
                color=color,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed * 0.5,
                life=8 + int(random.random() * 6)
            ))
            
    def update(self):
        """更新游戏状态"""
        if self.state != GameState.PLAYING:
            return
            
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.flash_frames > 0:
            self.flash_frames -= 1
            
        # 移动当前方块
        if self.current_block and self.current_block.get('moving', True):
            self.current_block['x'] += self.direction * self.speed
            if self.current_block['x'] <= 0 or self.current_block['x'] >= self.game_width - self.current_block['width']:
                self.direction *= -1
                
        # 更新粒子
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.01
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)
                
        # 更新弹出文字
        for sp in self.score_popups[:]:
            sp.y -= 0.15
            sp.frames -= 1
            if sp.frames <= 0:
                self.score_popups.remove(sp)
                
    def render(self) -> str:
        """渲染游戏画面"""
        output = '\\x1b[2J\\x1b[H'
        cols, rows = get_terminal_size()
        
        game_left = max(2, (cols - self.game_width - 2) // 2)
        game_top = max(2, (rows - self.game_height - 4) // 2)
        
        render_left = game_left
        render_top = game_top
        if self.shake_frames > 0:
            render_left += int((random.random() - 0.5) * 3)
            render_top += int((random.random() - 0.5) * 2)
            
        # 标题
        title = '══ 高塔堆叠 ══'
        title_x = (cols - len(title)) // 2
        output += move_cursor(1, title_x)
        output += f'{Colors.BOLD}{Colors.MAGENTA}{title}{Colors.RESET}'
        
        # 状态栏
        missed_display = '×' * self.missed + '○' * (self.max_missed - self.missed)
        stats = f'高度：{len(self.blocks)}  得分：{self.score}  失误：{missed_display}'
        output += move_cursor(3, (cols - len(stats)) // 2)
        output += f'{Colors.CYAN}{stats}{Colors.RESET}'
        
        # 边框
        output += move_cursor(render_top, render_left)
        output += f'{Colors.DIM}╔{"═" * self.game_width}╗{Colors.RESET}'
        for y in range(self.game_height):
            output += move_cursor(render_top + 1 + y, render_left)
            output += f'{Colors.DIM}║{Colors.RESET}'
            output += move_cursor(render_top + 1 + y, render_left + self.game_width + 1)
            output += f'{Colors.DIM}║{Colors.RESET}'
        output += move_cursor(render_top + self.game_height + 1, render_left)
        output += f'{Colors.DIM}╚{"═" * self.game_width}╝{Colors.RESET}'
        
        if self.state == GameState.NOT_STARTED:
            start_msg = '[ 按空格放置方块 ]'
            start_x = game_left + (self.game_width - len(start_msg)) // 2
            start_y = game_top + self.game_height // 2
            output += move_cursor(start_y, start_x)
            output += f'{Colors.BLINK}{Colors.MAGENTA}{start_msg}{Colors.RESET}'
            controls = '空格放置  ESC 菜单'
            output += move_cursor(start_y + 2, game_left + (self.game_width - len(controls)) // 2)
            output += f'{Colors.DIM}{controls}{Colors.RESET}'
        elif self.state == GameState.PAUSED:
            pause_msg = '══ 暂停 ══'
            output += move_cursor(render_top + self.game_height // 2, render_left + self.game_width // 2 - len(pause_msg) // 2)
            output += f'{Colors.BLINK}{Colors.CYAN}{pause_msg}{Colors.RESET}'
        elif self.state == GameState.GAME_OVER:
            over_msg = '══ 塔倒了！══'
            over_x = game_left + (self.game_width - len(over_msg)) // 2
            over_y = game_top + self.game_height // 2 - 1
            output += move_cursor(over_y, over_x)
            output += f'{Colors.BOLD}{Colors.RED}{over_msg}{Colors.RESET}'
            score_text = f'最终高度：{len(self.blocks)}  得分：{self.score}'
            output += move_cursor(over_y + 1, game_left + (self.game_width - len(score_text)) // 2)
            output += f'{Colors.CYAN}{score_text}{Colors.RESET}'
            restart = '[R] 重来  [Q] 退出'
            output += move_cursor(over_y + 3, game_left + (self.game_width - len(restart)) // 2)
            output += f'{Colors.DIM}{restart}{Colors.RESET}'
        else:
            # 绘制已放置的方块
            for block in self.blocks:
                sx = render_left + 1 + int(block['x'])
                sy = render_top + 1 + int(block['y'])
                bar = '█' * block['width']
                if block.get('perfect'):
                    output += move_cursor(sy, sx)
                    output += f'{Colors.BOLD}{Colors.YELLOW}{bar}{Colors.RESET}'
                else:
                    output += move_cursor(sy, sx)
                    output += f'{block["color"]}{bar}{Colors.RESET}'
                    
            # 绘制当前移动的方块
            if self.current_block:
                sx = render_left + 1 + int(self.current_block['x'])
                sy = render_top + 1 + int(self.current_block['y'])
                bar = '▓' * self.current_block['width']
                output += move_cursor(sy, sx)
                output += f'{self.current_block["color"]}{bar}{Colors.RESET}'
                
            # 绘制完美连击
            if self.perfect_streak >= 3:
                streak_msg = f'★ {self.perfect_streak}x PERFECT! ★'
                output += move_cursor(render_top + 2, render_left + (self.game_width - len(streak_msg)) // 2)
                output += f'{Colors.BOLD}{Colors.YELLOW}{streak_msg}{Colors.RESET}'
                
            # 绘制粒子
            for p in self.particles:
                sx = round(render_left + 1 + p.x)
                sy = round(render_top + 1 + p.y)
                if render_top < sy < render_top + self.game_height + 1:
                    output += move_cursor(sy, sx)
                    output += f'{p.color}{p.char}{Colors.RESET}'
                    
            # 绘制弹出文字
            for sp in self.score_popups:
                sx = round(render_left + 1 + sp.x)
                sy = round(render_top + 1 + sp.y)
                if sy > render_top:
                    output += move_cursor(sy, sx)
                    output += f'{sp.color}{sp.text}{Colors.RESET}'
                    
        return output
    
    def handle_input(self, key: str):
        """处理输入"""
        if self.state == GameState.NOT_STARTED:
            if key == ' ':
                self.state = GameState.PLAYING
            return
            
        if self.state == GameState.GAME_OVER:
            if key == 'r':
                self.init_game()
                self.state = GameState.PLAYING
            return
            
        if self.state == GameState.PAUSED:
            if key == 'escape':
                self.state = GameState.PLAYING
            return
            
        if self.state != GameState.PLAYING:
            if key == 'escape':
                self.state = GameState.PAUSED
            return
            
        if key == 'escape':
            self.state = GameState.PAUSED
        elif key == ' ':
            self.place_block()


# ============================================================================
# 主程序入口
# ============================================================================

class GameSelector:
    """游戏选择器"""
    
    GAMES = {
        'tetris': ('俄罗斯方块', TetrisGame),
        'space': ('太空侵略者', SpaceInvadersGame),
        'runner': ('无尽跑酷', RunnerGame),
        'crack': ('密码破解', CrackGame),
        'chopper': ('直升机', ChopperGame),
        'breakout': ('打砖块', BreakoutGame),
        'tower': ('高塔堆叠', TowerGame),
    }
    
    def __init__(self, console: Console):
        self.console = console
        self.selected_index = 0
        self.game_list = list(self.GAMES.keys())
        
    def render(self) -> str:
        """渲染选择菜单"""
        output = '\x1b[2J\x1b[H'
        cols, rows = get_terminal_size()
        
        title = '══ 超级复古游戏合集 ══'
        title_x = (cols - len(title)) // 2
        output += move_cursor(3, title_x)
        output += f'{Colors.BOLD}{Colors.CYAN}{title}{Colors.RESET}'
        
        subtitle = 'Hyper Retro Games Collection'
        sub_x = (cols - len(subtitle)) // 2
        output += move_cursor(5, sub_x)
        output += f'{Colors.DIM}{Colors.CYAN}{subtitle}{Colors.RESET}'
        
        menu_start = 8
        for i, game_key in enumerate(self.game_list):
            name, _ = self.GAMES[game_key]
            marker = '► ' if i == self.selected_index else '  '
            color = Colors.YELLOW if i == self.selected_index else Colors.WHITE
            line = f'{marker}{name}'
            line_x = (cols - len(line)) // 2
            output += move_cursor(menu_start + i * 2, line_x)
            output += f'{color}{line}{Colors.RESET}'
            
        footer = '↑↓ 选择  ENTER 确认  Q 退出'
        footer_x = (cols - len(footer)) // 2
        output += move_cursor(rows - 3, footer_x)
        output += f'{Colors.DIM}{Colors.CYAN}{footer}{Colors.RESET}'
        
        return output
    
    def handle_input(self, key: str) -> Optional[str]:
        """处理输入，返回选中的游戏或None"""
        if key in ['up', 'w'] and self.selected_index > 0:
            self.selected_index -= 1
        elif key in ['down', 's'] and self.selected_index < len(self.game_list) - 1:
            self.selected_index += 1
        elif key == 'enter':
            return self.game_list[self.selected_index]
        return None


def main():
    """主函数"""
    console = Console()
    hide_cursor()
    
    try:
        selector = GameSelector(console)
        current_game: Optional[GameController] = None
        game_key = None
        
        last_update = time.time()
        update_interval = 0.025  # 25ms = 40fps
        
        while True:
            # 获取输入
            import select
            import tty
            import termios
            
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':  # ESC序列
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A':
                                key = 'up'
                            elif ch3 == 'B':
                                key = 'down'
                            elif ch3 == 'C':
                                key = 'right'
                            elif ch3 == 'D':
                                key = 'left'
                            else:
                                key = ch3
                        else:
                            key = 'escape'
                    elif ch == '\n' or ch == '\r':
                        key = 'enter'
                    elif ch.lower() == 'q':
                        return
                    else:
                        key = ch.lower()
                    
                    if current_game:
                        current_game.handle_input(key)
                        if not current_game.running:
                            current_game = None
                            game_key = None
                    else:
                        selected = selector.handle_input(key)
                        if selected:
                            _, game_class = selector.GAMES[selected]
                            current_game = game_class(console)
                            current_game.init_game()
                            game_key = selected
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            
            # 更新和渲染
            now = time.time()
            if now - last_update >= update_interval:
                last_update = now
                
                if current_game:
                    current_game.update()
                    output = current_game.render()
                else:
                    output = selector.render()
                    
                print(output, end='', flush=True)
                
    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()


if __name__ == '__main__':
    main()
