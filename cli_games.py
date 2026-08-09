#!/usr/bin/env python3
"""
@hypersocial/cli-games - Python 版本
终端游戏集合：贪吃蛇、俄罗斯方块、2048、乒乓球等
使用 rich 库进行终端渲染

用法:
    python cli_games.py                    # 交互式游戏菜单
    python cli_games.py snake              # 直接启动贪吃蛇
    python cli_games.py --theme green      # 设置颜色主题
    python cli_games.py --list             # 列出所有游戏
"""

import sys
import random
import time
import os
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod

# 检查并导入 rich
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align
except ImportError:
    print("请安装 rich 库：pip install rich")
    sys.exit(1)


# ============================================================================
# 主题配置
# ============================================================================

class ThemeMode(str, Enum):
    """主题模式枚举"""
    CYAN = "cyan"
    AMBER = "amber"
    GREEN = "green"
    WHITE = "white"
    HOTPINK = "hotpink"
    BLOOD = "blood"
    ICE = "ice"
    BLADERUNNER = "bladerunner"
    TRON = "tron"
    KAWAII = "kawaii"
    NORD = "nord"
    BANANA = "banana"


@dataclass
class ThemeColors:
    """主题颜色定义"""
    name: str
    icon: str
    primary: str
    secondary: str
    bg: str = "#000000"


THEMES: Dict[ThemeMode, ThemeColors] = {
    ThemeMode.CYAN: ThemeColors("赛博朋克", "🔵", "#00D9FF", "#FF006E"),
    ThemeMode.AMBER: ThemeColors("辐射", "🟠", "#FFB000", "#FF6600"),
    ThemeMode.GREEN: ThemeColors("矩阵", "🟢", "#39FF14", "#00FF00"),
    ThemeMode.WHITE: ThemeColors("幽灵", "⚪", "#FFFFFF", "#88CCFF"),
    ThemeMode.HOTPINK: ThemeColors("合成波", "💖", "#FF6AC1", "#00D9FF"),
    ThemeMode.BLOOD: ThemeColors("鲜血", "🔴", "#FF3333", "#AA0000"),
    ThemeMode.ICE: ThemeColors("冰霜", "❄️", "#88FFFF", "#4488FF"),
    ThemeMode.BLADERUNNER: ThemeColors("银翼杀手", "🟧", "#FF6B35", "#00CED1"),
    ThemeMode.TRON: ThemeColors("创战纪", "🔷", "#6FFFE9", "#FF6B00"),
    ThemeMode.KAWAII: ThemeColors("可爱", "🌸", "#FFB7C5", "#FF69B4"),
    ThemeMode.NORD: ThemeColors("北欧", "🏔️", "#88C0D0", "#81A1C1"),
    ThemeMode.BANANA: ThemeColors("香蕉", "🍌", "#FFE135", "#FFA500"),
}

# 当前主题
current_theme = ThemeMode.CYAN


def set_theme(mode: str) -> None:
    """设置当前主题"""
    global current_theme
    try:
        current_theme = ThemeMode(mode.lower())
    except ValueError:
        pass


def get_theme_color() -> str:
    """获取当前主题的主颜色"""
    return THEMES[current_theme].primary


def get_theme_name() -> str:
    """获取当前主题名称"""
    return THEMES[current_theme].name


# ============================================================================
# 终端工具函数
# ============================================================================

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def hide_cursor():
    """隐藏光标"""
    print('\033[?25l', end='')


def show_cursor():
    """显示光标"""
    print('\033[?25h', end='')


def enter_alternate_buffer():
    """进入备用缓冲区"""
    print('\033[?1049h', end='')


def exit_alternate_buffer():
    """退出备用缓冲区"""
    print('\033[?1049l', end='')
    show_cursor()


def move_cursor(row: int, col: int):
    """移动光标到指定位置"""
    print(f'\033[{row};{col}H', end='')


def get_terminal_size() -> tuple:
    """获取终端大小"""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


# ============================================================================
# 输入处理
# ============================================================================

class KeyHandler:
    """键盘输入处理器"""
    
    def __init__(self):
        self.running = False
        self.key_queue: List[str] = []
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """开始监听键盘输入"""
        self.running = True
        self.thread = threading.Thread(target=self._read_keys, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止监听"""
        self.running = False
    
    def _read_keys(self):
        """读取键盘输入（Unix）"""
        import tty
        import termios
        
        if os.name != 'nt':
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while self.running:
                    try:
                        char = sys.stdin.read(1)
                        if char == '\x1b':  # ESC 序列
                            char2 = sys.stdin.read(1)
                            if char2 == '[':
                                char3 = sys.stdin.read(1)
                                if char3 == 'A':
                                    key = 'UP'
                                elif char3 == 'B':
                                    key = 'DOWN'
                                elif char3 == 'C':
                                    key = 'RIGHT'
                                elif char3 == 'D':
                                    key = 'LEFT'
                                else:
                                    key = char3
                            else:
                                key = 'ESC'
                        elif char == '\r':
                            key = 'ENTER'
                        elif char == '\x7f':
                            key = 'BACKSPACE'
                        elif char == ' ':
                            key = 'SPACE'
                        else:
                            key = char.upper() if char.isalpha() else char
                        
                        with self.lock:
                            self.key_queue.append(key)
                    except Exception:
                        break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def get_key(self) -> Optional[str]:
        """获取按键"""
        with self.lock:
            if self.key_queue:
                return self.key_queue.pop(0)
        return None
    
    def wait_for_key(self, timeout: float = 0.1) -> Optional[str]:
        """等待按键（带超时）"""
        start = time.time()
        while time.time() - start < timeout:
            key = self.get_key()
            if key:
                return key
            time.sleep(0.01)
        return None


# ============================================================================
# 游戏基类
# ============================================================================

@dataclass
class GameInfo:
    """游戏信息"""
    id: str
    name: str
    description: str


class GameController(ABC):
    """游戏控制器基类"""
    
    def __init__(self, console: Console):
        self.console = console
        self.running = False
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.paused = False
    
    @abstractmethod
    def run(self) -> bool:
        """运行游戏，返回是否继续"""
        pass
    
    @abstractmethod
    def handle_input(self, key: str) -> None:
        """处理输入"""
        pass
    
    def stop(self):
        """停止游戏"""
        self.running = False


# ============================================================================
# 贪吃蛇游戏
# ============================================================================

class SnakeGame(GameController):
    """贪吃蛇游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.snake: List[tuple] = []
        self.direction = 'RIGHT'
        self.next_direction = 'RIGHT'
        self.food: tuple = (0, 0)
        self.game_width = 40
        self.game_height = 15
        self.game_left = 2
        self.game_top = 4
    
    def init_game(self):
        """初始化游戏"""
        cols, rows = get_terminal_size()
        self.game_width = min(cols - 4, 50)
        self.game_height = min(rows - 10, 18)
        self.game_left = max(2, (cols - self.game_width - 2) // 2)
        self.game_top = max(3, (rows - self.game_height - 6) // 2)
        
        # 初始化蛇
        start_x = self.game_width // 2
        start_y = self.game_height // 2
        self.snake = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y),
        ]
        self.direction = 'RIGHT'
        self.next_direction = 'RIGHT'
        self.score = 0
        self.game_over = False
        self.spawn_food()
    
    def spawn_food(self):
        """生成食物"""
        while True:
            x = random.randint(1, self.game_width - 2)
            y = random.randint(1, self.game_height - 2)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break
    
    def update(self):
        """更新游戏状态"""
        if self.game_over or self.paused:
            return
        
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        
        if self.direction == 'UP':
            head_y -= 1
        elif self.direction == 'DOWN':
            head_y += 1
        elif self.direction == 'LEFT':
            head_x -= 1
        elif self.direction == 'RIGHT':
            head_x += 1
        
        # 检查碰撞
        if (head_x <= 0 or head_x >= self.game_width or
            head_y <= 0 or head_y >= self.game_height or
            (head_x, head_y) in self.snake):
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
            return
        
        self.snake.insert(0, (head_x, head_y))
        
        # 检查是否吃到食物
        if (head_x, head_y) == self.food:
            self.score += 10
            self.spawn_food()
        else:
            self.snake.pop()
    
    def render(self):
        """渲染游戏"""
        output = []
        output.append('\033[2J\033[H')  # 清屏
        
        theme_color = get_theme_color()
        
        # 标题
        title = [
            "█ █ █▄█ █▀█ █▀▀ █▀█   █▀▀ █▄ █ ▄▀█ █▄▀ █▀▀",
            "█▀█  █  █▀▀ ██▄ █▀▄   ▄▄█ █ ▀█ █▀█ █ █ ██▄",
        ]
        title_x = max(1, self.game_left + (self.game_width - len(title[0])) // 2)
        output.append(f'\033[{max(1, self.game_top - 3)};{title_x}H\033[1m{theme_color}{title[0]}\033[0m')
        output.append(f'\033[{max(1, self.game_top - 2)};{title_x}H\033[1m{theme_color}{title[1]}\033[0m')
        
        # 分数
        score_text = f"分数：{self.score:04d}  最高分：{self.high_score:04d}"
        output.append(f'\033[{max(2, self.game_top - 1)};{self.game_left}H{theme_color}{score_text}\033[0m')
        
        # 边框
        border = '═' * self.game_width
        output.append(f'\033[{self.game_top};{self.game_left}H{theme_color}╔{border}╗\033[0m')
        for y in range(1, self.game_height + 1):
            output.append(f'\033[{self.game_top + y};{self.game_left}H{theme_color}║\033[0m')
            output.append(f'\033[{self.game_top + y};{self.game_left + self.game_width + 1}H{theme_color}║\033[0m')
        output.append(f'\033[{self.game_top + self.game_height + 1};{self.game_left}H{theme_color}╚{border}╝\033[0m')
        
        if not self.game_over:
            if self.paused:
                pause_msg = "══ 暂停 ══"
                pause_x = self.game_left + (self.game_width - len(pause_msg)) // 2
                pause_y = self.game_top + self.game_height // 2 - 1
                output.append(f'\033[{pause_y};{pause_x}H\033[5m{theme_color}{pause_msg}\033[0m')
                output.append(f'\033[{pause_y + 2};{pause_x}H\033[2m↑↓←→ 移动  ENTER 继续\033[0m')
            else:
                # 绘制食物
                food_char = '◆'
                food_x = self.game_left + self.food[0] + 1
                food_y = self.game_top + self.food[1]
                output.append(f'\033[{food_y};{food_x}H\033[1;33m{food_char}\033[0m')
                
                # 绘制蛇
                for i, (sx, sy) in enumerate(self.snake):
                    char = '█' if i == 0 else '▓'
                    brightness = '\033[1m' if i == 0 else '\033[2m'
                    draw_x = self.game_left + sx + 1
                    draw_y = self.game_top + sy
                    output.append(f'\033[{draw_y};{draw_x}H{brightness}{theme_color}{char}\033[0m')
                
                hint = '[ESC] 菜单'
                output.append(f'\033[{self.game_top + self.game_height + 3};{self.game_left}H\033[2m{hint}\033[0m')
        else:
            over_msg = "══ 游戏结束 ══"
            over_x = self.game_left + (self.game_width - len(over_msg)) // 2
            over_y = self.game_top + self.game_height // 2 - 1
            output.append(f'\033[{over_y};{over_x}H\033[1;31m{over_msg}\033[0m')
            output.append(f'\033[{over_y + 2};{over_x}H{theme_color}最终分数：{self.score}\033[0m')
            output.append(f'\033[{over_y + 4};{over_x}H\033[2m[R] 重新开始  [Q] 退出\033[0m')
        
        self.console.print(''.join(output), end='')
    
    def handle_input(self, key: str) -> None:
        """处理输入"""
        if self.game_over:
            if key == 'R':
                self.init_game()
            elif key == 'Q':
                self.running = False
            return
        
        if self.paused:
            if key == 'ENTER':
                self.paused = False
            return
        
        if key == 'UP' or key == 'W':
            if self.direction != 'DOWN':
                self.next_direction = 'UP'
        elif key == 'DOWN' or key == 'S':
            if self.direction != 'UP':
                self.next_direction = 'DOWN'
        elif key == 'LEFT' or key == 'A':
            if self.direction != 'RIGHT':
                self.next_direction = 'LEFT'
        elif key == 'RIGHT' or key == 'D':
            if self.direction != 'LEFT':
                self.next_direction = 'RIGHT'
        elif key == 'ESC':
            self.paused = True
        elif key == 'Q':
            self.running = False
    
    def run(self) -> bool:
        """运行游戏"""
        self.init_game()
        self.running = True
        last_update = time.time()
        update_interval = 0.12  # 蛇的移动速度
        
        handler = KeyHandler()
        handler.start()
        
        try:
            enter_alternate_buffer()
            hide_cursor()
            
            while self.running:
                # 处理输入
                key = handler.wait_for_key(0.05)
                if key:
                    self.handle_input(key)
                
                # 更新游戏状态
                now = time.time()
                if now - last_update >= update_interval:
                    if not self.paused and not self.game_over:
                        self.update()
                    last_update = now
                
                # 渲染
                self.render()
                
                # 控制帧率
                time.sleep(0.025)
        finally:
            handler.stop()
            exit_alternate_buffer()
        
        return False  # 不返回菜单


# ============================================================================
# 2048 游戏
# ============================================================================

class Game2048(GameController):
    """2048 游戏"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.grid: List[List[int]] = []
        self.grid_size = 4
        self.cell_width = 6
    
    def init_game(self):
        """初始化游戏"""
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.score = 0
        self.game_over = False
        self.add_random_tile()
        self.add_random_tile()
    
    def add_random_tile(self):
        """添加随机方块"""
        empty_cells = []
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] == 0:
                    empty_cells.append((r, c))
        
        if empty_cells:
            r, c = random.choice(empty_cells)
            self.grid[r][c] = 2 if random.random() < 0.9 else 4
    
    def slide_line(self, line: List[int]) -> List[int]:
        """滑动一行"""
        # 移除零
        new_line = [x for x in line if x != 0]
        
        # 合并相同数字
        i = 0
        while i < len(new_line) - 1:
            if new_line[i] == new_line[i + 1]:
                new_line[i] *= 2
                self.score += new_line[i]
                new_line.pop(i + 1)
            i += 1
        
        # 补零
        while len(new_line) < self.grid_size:
            new_line.append(0)
        
        return new_line
    
    def move(self, direction: str) -> bool:
        """移动方块"""
        moved = False
        old_grid = [row[:] for row in self.grid]
        
        if direction == 'LEFT':
            for r in range(self.grid_size):
                self.grid[r] = self.slide_line(self.grid[r])
        elif direction == 'RIGHT':
            for r in range(self.grid_size):
                self.grid[r] = self.slide_line(self.grid[r][::-1])[::-1]
        elif direction == 'UP':
            for c in range(self.grid_size):
                col = [self.grid[r][c] for r in range(self.grid_size)]
                new_col = self.slide_line(col)
                for r in range(self.grid_size):
                    self.grid[r][c] = new_col[r]
        elif direction == 'DOWN':
            for c in range(self.grid_size):
                col = [self.grid[r][c] for r in range(self.grid_size)][::-1]
                new_col = self.slide_line(col)[::-1]
                for r in range(self.grid_size):
                    self.grid[r][c] = new_col[r]
        
        moved = self.grid != old_grid
        
        if moved:
            self.add_random_tile()
            if self.check_game_over():
                self.game_over = True
        
        return moved
    
    def check_game_over(self) -> bool:
        """检查游戏是否结束"""
        # 检查是否有空格
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] == 0:
                    return False
        
        # 检查是否有可合并的相邻方块
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                val = self.grid[r][c]
                if c < self.grid_size - 1 and val == self.grid[r][c + 1]:
                    return False
                if r < self.grid_size - 1 and val == self.grid[r + 1][c]:
                    return False
        
        return True
    
    def render(self):
        """渲染游戏"""
        output = []
        output.append('\033[2J\033[H')
        
        theme_color = get_theme_color()
        cols, rows = get_terminal_size()
        
        # 计算位置
        game_width = self.grid_size * (self.cell_width + 1) + 1
        game_height = self.grid_size * 3 + 1
        game_left = max(2, (cols - game_width) // 2)
        game_top = max(4, (rows - game_height - 6) // 2)
        
        # 标题
        title = "═══ 2048 ═══"
        title_x = max(1, game_left + (game_width - len(title)) // 2)
        output.append(f'\033[{game_top - 3};{title_x}H\033[1m{theme_color}{title}\033[0m')
        
        # 分数
        score_text = f"分数：{self.score}"
        output.append(f'\033[{game_top - 1};{game_left}H{theme_color}{score_text}\033[0m')
        
        # 绘制网格
        color_map = {
            0: '\033[2m',
            2: '\033[37m',
            4: '\033[36m',
            8: '\033[33m',
            16: '\033[35m',
            32: '\033[31m',
            64: '\033[1;31m',
            128: '\033[1;33m',
            256: '\033[1;32m',
            512: '\033[1;36m',
            1024: '\033[1;35m',
            2048: '\033[1;37m',
        }
        
        for r in range(self.grid_size):
            # 上边框
            h_line = '─' * self.cell_width
            output.append(f'\033[{game_top + r * 3};{game_left}H{theme_color}┌{h_line}┐\033[0m')
            for c in range(1, self.grid_size):
                output.append(f'\033[{game_top + r * 3};{game_left + c * (self.cell_width + 1)}H{theme_color}┬\033[0m')
            output.append(f'\033[{game_top + r * 3};{game_left + game_width - 1}H┐\033[0m')
            
            # 数字行
            num_row = f'\033[{game_top + r * 3 + 1};{game_left}H{theme_color}│\033[0m'
            output.append(num_row)
            for c in range(self.grid_size):
                val = self.grid[r][c]
                color = color_map.get(val, '\033[1;37m')
                cell_str = str(val) if val != 0 else ''
                cell_str = cell_str.center(self.cell_width)
                output.append(f'\033[{game_top + r * 3 + 1};{game_left + 1 + c * (self.cell_width + 1)}H{color}{cell_str}\033[0m')
                if c < self.grid_size - 1:
                    output.append(f'\033[{game_top + r * 3 + 1};{game_left + (c + 1) * (self.cell_width + 1) - 1}H{theme_color}│\033[0m')
            output.append(f'\033[{game_top + r * 3 + 1};{game_left + game_width}H{theme_color}│\033[0m')
            
            # 下边框
            output.append(f'\033[{game_top + r * 3 + 2};{game_left}H{theme_color}└{h_line}┘\033[0m')
            for c in range(1, self.grid_size):
                output.append(f'\033[{game_top + r * 3 + 2};{game_left + c * (self.cell_width + 1)}H{theme_color}┴\033[0m')
            output.append(f'\033[{game_top + r * 3 + 2};{game_left + game_width - 1}H┘\033[0m')
        
        # 底部边框
        bottom_y = game_top + self.grid_size * 3
        h_line = '─' * self.cell_width
        output.append(f'\033[{bottom_y};{game_left}H{theme_color}└{h_line}┘\033[0m')
        for c in range(1, self.grid_size):
            output.append(f'\033[{bottom_y};{game_left + c * (self.cell_width + 1)}H{theme_color}└\033[0m')
        output.append(f'\033[{bottom_y};{game_left + game_width - 1}H┘\033[0m')
        
        if self.game_over:
            over_msg = "游戏结束!"
            over_x = game_left + (game_width - len(over_msg)) // 2
            over_y = game_top + self.grid_size * 3 + 2
            output.append(f'\033[{over_y};{over_x}H\033[1;31m{over_msg}\033[0m')
            output.append(f'\033[{over_y + 1};{over_x}H\033[2m[R] 重来  [Q] 退出\033[0m')
        else:
            hint = "↑↓←→ 移动  [Q] 退出"
            hint_x = game_left + (game_width - len(hint)) // 2
            output.append(f'\033[{bottom_y + 2};{hint_x}H\033[2m{hint}\033[0m')
        
        self.console.print(''.join(output), end='')
    
    def handle_input(self, key: str) -> None:
        """处理输入"""
        if self.game_over:
            if key == 'R':
                self.init_game()
            elif key == 'Q':
                self.running = False
            return
        
        if key in ['UP', 'W']:
            self.move('UP')
        elif key in ['DOWN', 'S']:
            self.move('DOWN')
        elif key in ['LEFT', 'A']:
            self.move('LEFT')
        elif key in ['RIGHT', 'D']:
            self.move('RIGHT')
        elif key == 'Q':
            self.running = False
    
    def run(self) -> bool:
        """运行游戏"""
        self.init_game()
        self.running = True
        
        handler = KeyHandler()
        handler.start()
        
        try:
            enter_alternate_buffer()
            hide_cursor()
            
            while self.running:
                key = handler.wait_for_key(0.05)
                if key:
                    self.handle_input(key)
                self.render()
                time.sleep(0.05)
        finally:
            handler.stop()
            exit_alternate_buffer()
        
        return False


# ============================================================================
# 乒乓球游戏
# ============================================================================

class PongGame(GameController):
    """乒乓球游戏（单人版）"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.paddle_y = 0
        self.ball_x = 0
        self.ball_y = 0
        self.ball_dx = 1
        self.ball_dy = 1
        self.game_width = 40
        self.game_height = 15
        self.paddle_height = 4
        self.ai_speed = 0.3
    
    def init_game(self):
        """初始化游戏"""
        cols, rows = get_terminal_size()
        self.game_width = min(cols - 4, 50)
        self.game_height = min(rows - 10, 18)
        
        self.paddle_y = self.game_height // 2 - self.paddle_height // 2
        self.reset_ball()
        self.score = 0
        self.game_over = False
    
    def reset_ball(self):
        """重置球的位置"""
        self.ball_x = self.game_width // 2
        self.ball_y = self.game_height // 2
        self.ball_dx = random.choice([-1, 1])
        self.ball_dy = random.choice([-1, 1])
    
    def update(self):
        """更新游戏状态"""
        if self.game_over:
            return
        
        # 移动球
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        # 上下墙壁反弹
        if self.ball_y <= 0 or self.ball_y >= self.game_height - 1:
            self.ball_dy = -self.ball_dy
        
        # AI 控制右侧挡板
        paddle_center = self.paddle_y + self.paddle_height // 2
        if paddle_center < self.ball_y - 1:
            self.paddle_y += self.ai_speed
        elif paddle_center > self.ball_y + 1:
            self.paddle_y -= self.ai_speed
        self.paddle_y = max(0, min(self.game_height - self.paddle_height, self.paddle_y))
        
        # 左侧挡板（玩家）检测
        if self.ball_x <= 1:
            if (self.ball_y >= self.paddle_y and 
                self.ball_y < self.paddle_y + self.paddle_height):
                self.ball_dx = -self.ball_dx
                self.ball_dx = min(abs(self.ball_dx) + 0.2, 2)  # 加速
                self.score += 1
            else:
                self.game_over = True
        
        # 右侧墙壁
        if self.ball_x >= self.game_width - 1:
            self.ball_dx = -self.ball_dx
    
    def render(self):
        """渲染游戏"""
        output = []
        output.append('\033[2J\033[H')
        
        theme_color = get_theme_color()
        cols, rows = get_terminal_size()
        
        game_left = max(2, (cols - self.game_width - 2) // 2)
        game_top = max(4, (rows - self.game_height - 6) // 2)
        
        # 标题
        title = "═══ 乒乓球 ═══"
        title_x = max(1, game_left + (self.game_width - len(title)) // 2)
        output.append(f'\033[{game_top - 3};{title_x}H\033[1m{theme_color}{title}\033[0m')
        
        # 分数
        output.append(f'\033[{game_top - 1};{game_left}H{theme_color}分数：{self.score}\033[0m')
        
        # 边框
        border = '─' * self.game_width
        output.append(f'\033[{game_top};{game_left}H{theme_color}╔{border}╗\033[0m')
        for y in range(1, self.game_height + 1):
            output.append(f'\033[{game_top + y};{game_left}H{theme_color}║\033[0m')
            output.append(f'\033[{game_top + y};{game_left + self.game_width + 1}H{theme_color}║\033[0m')
        output.append(f'\033[{game_top + self.game_height + 1};{game_left}H{theme_color}╚{border}╝\033[0m')
        
        if not self.game_over:
            # 绘制左侧挡板（玩家）
            for i in range(self.paddle_height):
                py = int(self.paddle_y) + i
                if 0 <= py < self.game_height:
                    output.append(f'\033[{game_top + py + 1};{game_left + 1}H{theme_color}█\033[0m')
            
            # 绘制右侧挡板（AI）
            ai_x = self.game_width - 2
            for i in range(self.paddle_height):
                py = int(self.paddle_y) + i
                if 0 <= py < self.game_height:
                    output.append(f'\033[{game_top + py + 1};{game_left + ai_x}H{theme_color}█\033[0m')
            
            # 绘制球
            ball_char = '●'
            bx = game_left + int(self.ball_x) + 1
            by = game_top + int(self.ball_y) + 1
            output.append(f'\033[{by};{bx}H\033[1;33m{ball_char}\033[0m')
            
            # 中线
            for y in range(1, self.game_height, 2):
                mid_x = game_left + self.game_width // 2
                output.append(f'\033[{game_top + y};{mid_x}H\033[2m·\033[0m')
            
            hint = "↑↓ 移动挡板  [Q] 退出"
            output.append(f'\033[{game_top + self.game_height + 3};{game_left}H\033[2m{hint}\033[0m')
        else:
            over_msg = "游戏结束!"
            over_x = game_left + (self.game_width - len(over_msg)) // 2
            over_y = game_top + self.game_height // 2
            output.append(f'\033[{over_y};{over_x}H\033[1;31m{over_msg}\033[0m')
            output.append(f'\033[{over_y + 2};{over_x}H{theme_color}最终分数：{self.score}\033[0m')
            output.append(f'\033[{over_y + 4};{over_x}H\033[2m[R] 重来  [Q] 退出\033[0m')
        
        self.console.print(''.join(output), end='')
    
    def handle_input(self, key: str) -> None:
        """处理输入"""
        if self.game_over:
            if key == 'R':
                self.init_game()
            elif key == 'Q':
                self.running = False
            return
        
        if key in ['UP', 'W']:
            self.paddle_y = max(0, self.paddle_y - 1)
        elif key in ['DOWN', 'S']:
            self.paddle_y = min(self.game_height - self.paddle_height, self.paddle_y + 1)
        elif key == 'Q':
            self.running = False
    
    def run(self) -> bool:
        """运行游戏"""
        self.init_game()
        self.running = True
        last_update = time.time()
        update_interval = 0.08
        
        handler = KeyHandler()
        handler.start()
        
        try:
            enter_alternate_buffer()
            hide_cursor()
            
            while self.running:
                key = handler.wait_for_key(0.03)
                if key:
                    self.handle_input(key)
                
                now = time.time()
                if now - last_update >= update_interval:
                    self.update()
                    last_update = now
                
                self.render()
                time.sleep(0.03)
        finally:
            handler.stop()
            exit_alternate_buffer()
        
        return False


# ============================================================================
# 猜词游戏（Hangman）
# ============================================================================

class HangmanGame(GameController):
    """猜词游戏"""
    
    WORDS = [
        "PYTHON", "PROGRAM", "COMPUTER", "TERMINAL", "GAME",
        "SNAKE", "TETRIS", "PUZZLE", "CODE", "DEVELOPER",
        "ALGORITHM", "VARIABLE", "FUNCTION", "LOOP", "STRING",
        "ARRAY", "OBJECT", "CLASS", "METHOD", "DEBUG",
    ]
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.word = ""
        self.guessed: set = set()
        self.wrong_guesses = 0
        self.max_wrong = 6
    
    def init_game(self):
        """初始化游戏"""
        self.word = random.choice(self.WORDS)
        self.guessed = set()
        self.wrong_guesses = 0
        self.game_over = False
        self.score = 0
    
    def is_won(self) -> bool:
        """检查是否获胜"""
        return all(c in self.guessed for c in self.word)
    
    def is_lost(self) -> bool:
        """检查是否失败"""
        return self.wrong_guesses >= self.max_wrong
    
    def render(self):
        """渲染游戏"""
        output = []
        output.append('\033[2J\033[H')
        
        theme_color = get_theme_color()
        cols, rows = get_terminal_size()
        
        game_width = 50
        game_left = max(2, (cols - game_width) // 2)
        game_top = max(4, (rows - 20) // 2)
        
        # 标题
        title = "═══ 猜词游戏 ═══"
        title_x = max(1, game_left + (game_width - len(title)) // 2)
        output.append(f'\033[{game_top - 2};{title_x}H\033[1m{theme_color}{title}\033[0m')
        
        # 绘制小人
        hangman_art = [
            "  ┌─────┐ ",
            f"  │ {'O' if self.wrong_guesses >= 1 else ' '}     │ ",
            f"  │ {'/' if self.wrong_guesses >= 2 else ' '}{'|' if self.wrong_guesses >= 2 else ' '}{'\\' if self.wrong_guesses >= 3 else ' '}    │ ",
            f"  │ {'/' if self.wrong_guesses >= 4 else ' '} {' ' if self.wrong_guesses < 5 else '\\'}   │ ",
            "  │       │ ",
            " ─┴───────┴─ ",
        ]
        
        art_left = game_left + 2
        for i, line in enumerate(hangman_art):
            output.append(f'\033[{game_top + i};{art_left}H{theme_color}{line}\033[0m')
        
        # 显示单词
        display_word = ' '.join(c if c in self.guessed else '_' for c in self.word)
        word_y = game_top + 8
        word_x = game_left + 20
        output.append(f'\033[{word_y};{word_x}H\033[1m{display_word}\033[0m')
        
        # 错误次数
        wrong_y = game_top + 10
        output.append(f'\033[{wrong_y};{word_x}H\033[2m错误：{self.wrong_guesses}/{self.max_wrong}\033[0m')
        
        # 已猜字母
        guessed_str = ' '.join(sorted(self.guessed)) if self.guessed else '无'
        guessed_y = game_top + 12
        output.append(f'\033[{guessed_y};{word_x}H\033[2m已猜：{guessed_str}\033[0m')
        
        if self.is_won():
            win_msg = "🎉 你赢了！🎉"
            msg_x = word_x + (len(display_word) - len(win_msg)) // 2
            output.append(f'\033[{word_y + 3};{msg_x}H\033[1;32m{win_msg}\033[0m')
            output.append(f'\033[{word_y + 5};{word_x}H\033[2m[R] 再来一局  [Q] 退出\033[0m')
        elif self.is_lost():
            lose_msg = f"😢 游戏结束！单词是：{self.word}"
            output.append(f'\033[{word_y + 3};{word_x}H\033[1;31m{lose_msg}\033[0m')
            output.append(f'\033[{word_y + 5};{word_x}H\033[2m[R] 再来一局  [Q] 退出\033[0m')
        else:
            hint = "输入 A-Z 猜字母  [Q] 退出"
            output.append(f'\033[{word_y + 5};{word_x}H\033[2m{hint}\033[0m')
        
        self.console.print(''.join(output), end='')
    
    def handle_input(self, key: str) -> None:
        """处理输入"""
        if self.is_won() or self.is_lost():
            if key == 'R':
                self.init_game()
            elif key == 'Q':
                self.running = False
            return
        
        if key == 'Q':
            self.running = False
            return
        
        # 处理字母输入
        if len(key) == 1 and key.isalpha():
            letter = key.upper()
            if letter not in self.guessed:
                self.guessed.add(letter)
                if letter not in self.word:
                    self.wrong_guesses += 1
                
                if self.is_won() or self.is_lost():
                    self.game_over = True
    
    def run(self) -> bool:
        """运行游戏"""
        self.init_game()
        self.running = True
        
        handler = KeyHandler()
        handler.start()
        
        try:
            enter_alternate_buffer()
            hide_cursor()
            
            while self.running:
                key = handler.wait_for_key(0.05)
                if key:
                    self.handle_input(key)
                self.render()
                time.sleep(0.05)
        finally:
            handler.stop()
            exit_alternate_buffer()
        
        return False


# ============================================================================
# 井字棋游戏
# ============================================================================

class TicTacToeGame(GameController):
    """井字棋游戏（双人对战）"""
    
    def __init__(self, console: Console):
        super().__init__(console)
        self.board: List[str] = []
        self.current_player = 'X'
        self.ai_enabled = True
    
    def init_game(self):
        """初始化游戏"""
        self.board = [' '] * 9
        self.current_player = 'X'
        self.game_over = False
        self.score = 0
    
    def check_winner(self) -> Optional[str]:
        """检查获胜者"""
        lines = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # 横
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # 竖
            [0, 4, 8], [2, 4, 6],              # 斜
        ]
        
        for line in lines:
            a, b, c = line
            if self.board[a] == self.board[b] == self.board[c] != ' ':
                return self.board[a]
        
        if ' ' not in self.board:
            return 'T'  # 平局
        
        return None
    
    def minimax(self, board: List[str], depth: int, is_maximizing: bool) -> int:
        """Minimax 算法"""
        winner = self.check_winner_on_board(board)
        
        if winner == 'O':
            return 10 - depth
        elif winner == 'X':
            return depth - 10
        elif winner == 'T':
            return 0
        
        if is_maximizing:
            best_score = -float('inf')
            for i in range(9):
                if board[i] == ' ':
                    board[i] = 'O'
                    score = self.minimax(board, depth + 1, False)
                    board[i] = ' '
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = float('inf')
            for i in range(9):
                if board[i] == ' ':
                    board[i] = 'X'
                    score = self.minimax(board, depth + 1, True)
                    board[i] = ' '
                    best_score = min(score, best_score)
            return best_score
    
    def check_winner_on_board(self, board: List[str]) -> Optional[str]:
        """检查棋盘上的获胜者"""
        lines = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6],
        ]
        
        for line in lines:
            a, b, c = line
            if board[a] == board[b] == board[c] != ' ':
                return board[a]
        
        if ' ' not in board:
            return 'T'
        
        return None
    
    def ai_move(self):
        """AI 移动"""
        best_score = -float('inf')
        best_move = 4  # 优先中心
        
        for i in range(9):
            if self.board[i] == ' ':
                self.board[i] = 'O'
                score = self.minimax(self.board, 0, False)
                self.board[i] = ' '
                if score > best_score:
                    best_score = score
                    best_move = i
        
        self.board[best_move] = 'O'
    
    def render(self):
        """渲染游戏"""
        output = []
        output.append('\033[2J\033[H')
        
        theme_color = get_theme_color()
        cols, rows = get_terminal_size()
        
        game_width = 20
        game_left = max(2, (cols - game_width) // 2)
        game_top = max(4, (rows - 15) // 2)
        
        # 标题
        title = "═══ 井字棋 ═══"
        title_x = max(1, game_left + (game_width - len(title)) // 2)
        output.append(f'\033[{game_top - 2};{title_x}H\033[1m{theme_color}{title}\033[0m')
        
        # 绘制棋盘
        for r in range(3):
            y = game_top + r * 3
            output.append(f'\033[{y};{game_left}H{theme_color}   │   │   \033[0m')
            output.append(f'\033[{y + 1};{game_left}H{theme_color}─┼───┼───\033[0m')
        
        # 清除最后一行横线
        output.append(f'\033[{game_top + 9};{game_left}H           \033[0m')
        
        # 填充棋子
        for i, cell in enumerate(self.board):
            r, c = i // 3, i % 3
            y = game_top + r * 3
            x = game_left + c * 4 + 1
            
            if cell == 'X':
                output.append(f'\033[{y};{x}H\033[1;36mX\033[0m')
            elif cell == 'O':
                output.append(f'\033[{y};{x}H\033[1;33mO\033[0m')
        
        # 当前玩家
        player_text = f"当前：{self.current_player}"
        output.append(f'\033[{game_top + 11};{game_left}H{theme_color}{player_text}\033[0m')
        
        winner = self.check_winner()
        if winner:
            if winner == 'T':
                msg = "平局！"
            else:
                msg = f"玩家 {winner} 获胜！"
            output.append(f'\033[{game_top + 13};{game_left}H\033[1;32m{msg}\033[0m')
            output.append(f'\033[{game_top + 15};{game_left}H\033[2m[R] 重来  [Q] 退出\033[0m')
        else:
            output.append(f'\033[{game_top + 15};{game_left}H\033[2m1-9 选择位置  [Q] 退出\033[0m')
        
        self.console.print(''.join(output), end='')
    
    def handle_input(self, key: str) -> None:
        """处理输入"""
        winner = self.check_winner()
        
        if winner:
            if key == 'R':
                self.init_game()
            elif key == 'Q':
                self.running = False
            return
        
        if key == 'Q':
            self.running = False
            return
        
        # 数字键选择位置
        if key in '123456789':
            pos = int(key) - 1
            if 0 <= pos < 9 and self.board[pos] == ' ':
                self.board[pos] = self.current_player
                
                if not self.check_winner():
                    self.current_player = 'O' if self.current_player == 'X' else 'X'
                    
                    # AI 回合
                    if self.ai_enabled and self.current_player == 'O':
                        self.ai_move()
                        if not self.check_winner():
                            self.current_player = 'X'
    
    def run(self) -> bool:
        """运行游戏"""
        self.init_game()
        self.running = True
        
        handler = KeyHandler()
        handler.start()
        
        try:
            enter_alternate_buffer()
            hide_cursor()
            
            while self.running:
                key = handler.wait_for_key(0.05)
                if key:
                    self.handle_input(key)
                self.render()
                time.sleep(0.05)
        finally:
            handler.stop()
            exit_alternate_buffer()
        
        return False


# ============================================================================
# 游戏菜单
# ============================================================================

GAMES: List[GameInfo] = [
    GameInfo("snake", "贪吃蛇", "吃掉食物，越长越长"),
    GameInfo("2048", "2048", "滑动合并数字方块"),
    GameInfo("pong", "乒乓球", "经典弹球游戏"),
    GameInfo("hangman", "猜词游戏", "猜出隐藏的单词"),
    GameInfo("tictactoe", "井字棋", "三子连线获胜"),
]


def create_game(game_id: str, console: Console) -> Optional[GameController]:
    """创建游戏实例"""
    games_map = {
        "snake": SnakeGame,
        "2048": Game2048,
        "pong": PongGame,
        "hangman": HangmanGame,
        "tictactoe": TicTacToeGame,
    }
    
    game_class = games_map.get(game_id)
    if game_class:
        return game_class(console)
    return None


def show_menu(console: Console) -> Optional[str]:
    """显示游戏菜单"""
    selected = 0
    running = True
    
    handler = KeyHandler()
    handler.start()
    
    try:
        while running:
            output = []
            output.append('\033[2J\033[H')
            
            theme_color = get_theme_color()
            theme_name = get_theme_name()
            cols, rows = get_terminal_size()
            
            # 标题
            title = [
                "█ █ █▄█ █▀█ █▀▀ █▀█   █▀▀ █▄ █ ▄▀█ █▄▀ █▀▀",
                "█▀█  █  █▀▀ ██▄ █▀▄   ▄▄█ █ ▀█ █▀█ █ █ ██▄",
            ]
            title_x = max(1, (cols - len(title[0])) // 2)
            output.append(f'\033[3;{title_x}H\033[1m{theme_color}{title[0]}\033[0m')
            output.append(f'\033[4;{title_x}H\033[1m{theme_color}{title[1]}\033[0m')
            
            subtitle = f"终端游戏集合 - 主题：{theme_name}"
            output.append(f'\033[6;{(cols - len(subtitle)) // 2}H\033[2m{subtitle}\033[0m')
            
            # 游戏列表
            menu_width = 45
            menu_left = max(2, (cols - menu_width) // 2)
            menu_top = 9
            
            # 边框
            output.append(f'\033[{menu_top};{menu_left}H{theme_color}╔{"═" * menu_width}╗\033[0m')
            for i in range(len(GAMES)):
                output.append(f'\033[{menu_top + 1 + i};{menu_left}H{theme_color}║\033[0m')
                output.append(f'\033[{menu_top + 1 + i};{menu_left + menu_width + 1}H{theme_color}║\033[0m')
            output.append(f'\033[{menu_top + 1 + len(GAMES)};{menu_left}H{theme_color}╚{"═" * menu_width}╝\033[0m')
            
            # 游戏选项
            for i, game in enumerate(GAMES):
                y = menu_top + 1 + i
                x = menu_left + 2
                
                if i == selected:
                    output.append(f'\033[{y};{x}H\033[1;30;106m ► {game.name} - {game.description} ◄ \033[0m')
                else:
                    output.append(f'\033[{y};{x}H  {i + 1}. {game.name} - {game.description} ')
            
            # 底部提示
            controls = "↑↓ 选择  ENTER 确认  Q 退出"
            output.append(f'\033[{rows - 2};{(cols - len(controls)) // 2}H\033[2m{controls}\033[0m')
            
            theme_hint = f"--theme <主题> 切换主题 (cyan/green/amber/...)"
            output.append(f'\033[{rows - 1};{(cols - len(theme_hint)) // 2}H\033[2m{theme_hint}\033[0m')
            
            console.print(''.join(output), end='')
            
            # 处理输入
            key = handler.wait_for_key(0.05)
            if key == 'UP' or key == 'W':
                selected = (selected - 1) % len(GAMES)
            elif key == 'DOWN' or key == 'S':
                selected = (selected + 1) % len(GAMES)
            elif key == 'ENTER':
                return GAMES[selected].id
            elif key in '12345':
                idx = int(key) - 1
                if 0 <= idx < len(GAMES):
                    return GAMES[idx].id
            elif key == 'Q':
                running = False
    
    finally:
        handler.stop()
    
    return None


def print_help():
    """打印帮助信息"""
    help_text = """
@hypersocial/cli-games — Python 终端游戏

用法:
    python cli_games.py                    交互式游戏菜单
    python cli_games.py <游戏>             直接启动游戏
    python cli_games.py --theme <主题>     设置颜色主题
    python cli_games.py --list             列出所有游戏
    python cli_games.py --help             显示帮助

游戏:
"""
    for game in GAMES:
        help_text += f"    {game.id:<15} {game.description}\n"
    
    help_text += """
主题:
    cyan (默认), amber, green, white, hotpink, blood, ice,
    bladerunner, tron, kawaii, nord, banana

控制:
    方向键 / WASD    移动 / 导航
    Enter            确认 / 选择
    ESC              暂停菜单
    Q                退出
"""
    print(help_text)


def print_list():
    """列出所有游戏"""
    print("\n可用游戏:")
    for game in GAMES:
        print(f"  {game.id:<15} {game.description}")
    print()


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    args = sys.argv[1:]
    
    # 解析参数
    if '--help' in args or '-h' in args:
        print_help()
        return
    
    if '--list' in args or '-l' in args:
        print_list()
        return
    
    # 主题设置
    theme_idx = -1
    for i, arg in enumerate(args):
        if arg == '--theme' and i + 1 < len(args):
            theme_idx = i
            set_theme(args[i + 1])
            break
    
    # 移除主题参数
    if theme_idx >= 0:
        args = args[:theme_idx] + args[theme_idx + 2:]
    
    console = Console()
    
    # 直接启动游戏
    if args:
        game_id = args[0].lower()
        game = create_game(game_id, console)
        if game:
            game.run()
        else:
            print(f"未知游戏：{game_id}")
            print(f"可用游戏：{', '.join(g.id for g in GAMES)}")
    else:
        # 显示菜单
        while True:
            game_id = show_menu(console)
            if game_id:
                game = create_game(game_id, console)
                if game:
                    game.run()
            else:
                break
        
        clear_screen()
        print("感谢游玩！再见！👋")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        show_cursor()
        exit_alternate_buffer()
        print("\n再见！👋")
    except Exception as e:
        show_cursor()
        exit_alternate_buffer()
        print(f"\n发生错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
