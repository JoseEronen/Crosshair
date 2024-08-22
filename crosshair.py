import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item
import threading
import os
import sys
import json

class CrosshairApp:
    def __init__(self):
        self.config_file = "crosshair_config.json"
        self.circle_radius = 3
        self.circle_center = (0, 0)
        self.is_moving = False
        self.is_visible = True
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.crosshair_color = (255, 0, 0)
        self.crosshair_alpha = 255
        self.crosshair_type = "circle"
        self.crosshair_image = None
        self.red_dot_radius = 2
        self.crosshair_thickness = 3  # Oletuspaksuus

        self.startup_image = None
        self.startup_duration = 3000
        self.version = "0.3.1"

        self.load_settings()
        self.setup_tkinter()
        self.setup_tray_icon()

    def load_settings(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                settings = json.load(file)
                self.circle_radius = settings.get('circle_radius', self.circle_radius)
                self.crosshair_color = tuple(settings.get('crosshair_color', self.crosshair_color))
                self.crosshair_alpha = settings.get('crosshair_alpha', self.crosshair_alpha)
                self.crosshair_type = settings.get('crosshair_type', self.crosshair_type)
                self.red_dot_radius = settings.get('red_dot_radius', self.red_dot_radius)
                self.crosshair_thickness = settings.get('crosshair_thickness', self.crosshair_thickness)
                self.crosshair_image_path = settings.get('crosshair_image_path', None)
                if self.crosshair_image_path and os.path.exists(self.crosshair_image_path):
                    self.crosshair_image = Image.open(self.crosshair_image_path).convert("RGBA")

    def save_settings(self):
        settings = {
            'circle_radius': self.circle_radius,
            'crosshair_color': self.crosshair_color,
            'crosshair_alpha': self.crosshair_alpha,
            'crosshair_type': self.crosshair_type,
            'red_dot_radius': self.red_dot_radius,
            'crosshair_thickness': self.crosshair_thickness,
            'crosshair_image_path': self.crosshair_image_path
        }
        with open(self.config_file, 'w') as file:
            json.dump(settings, file)

    def setup_tkinter(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f'{screen_width}x{screen_height}+0+0')

        self.root.attributes('-transparentcolor', '#000000')

        self.canvas = tk.Canvas(self.root, bg='#000000', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.circle_center = (screen_width // 2, screen_height // 2)

        self.show_startup_image()

        self.canvas.bind('<Button-1>', self.start_move)
        self.canvas.bind('<B1-Motion>', self.move)

        self.root.bind('<F9>', self.close)

        self.root.update()

    def setup_tray_icon(self):
        def create_image():
            width, height = 64, 64
            icon_image = Image.new('RGB', (width, height), color=(0, 0, 0))
            draw = ImageDraw.Draw(icon_image)
            
            draw.line([32, 16, 32, 48], fill="red", width=4)
            draw.line([16, 32, 48, 32], fill="red", width=4)
            return icon_image

        def on_quit(icon, item):
            self.save_settings()
            self.quit_app()

        def on_change_size_bigger(icon, item):
            self.circle_radius = int(self.circle_radius * 1.4)
            self.update_crosshair()

        def on_change_size_smaller(icon, item):
            self.circle_radius = int(self.circle_radius / 1.2)
            self.update_crosshair()

        def on_center_crosshair(icon, item):
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.circle_center = (screen_width // 2, screen_height // 2)
            self.update_crosshair()

        def on_move_crosshair(icon, item):
            self.is_moving = not self.is_moving
            self.update_move_button_text()

        def on_hide(icon, item):
            if self.is_visible:
                self.root.withdraw()
                self.is_visible = False
            else:
                self.root.deiconify()
                self.is_visible = True

        def open_color_picker(icon, item):
            color_picker = tk.Toplevel(self.root)
            color_picker.title("Configure Crosshair")
            color_picker.geometry("300x800")

            color_picker_label = tk.Label(color_picker, text="CROSSHAIR SETTINGS", font=("Arial", 12))
            color_picker_label.pack(pady=20)

            tk.Label(color_picker, text="Type").pack(pady=0)
            type_var = tk.StringVar(value=self.crosshair_type)
            types = ["circle", "cross", "red_dot"]
            type_menu = tk.OptionMenu(color_picker, type_var, *types)
            type_menu.pack(pady=0)

            tk.Label(color_picker, text="Size").pack()
            size_slider = tk.Scale(color_picker, from_=1, to=500, orient=tk.HORIZONTAL)
            size_slider.set(self.circle_radius)
            size_slider.pack(fill=tk.X, padx=10, pady=0)

            def update_slider_colors():
                red_slider.config(troughcolor="#ff9999")
                green_slider.config(troughcolor="#99ff99")
                blue_slider.config(troughcolor="#9999ff")

            def create_colored_slider(master, color, value):
                slider = tk.Scale(master, from_=0, to=255, orient=tk.HORIZONTAL, bg=color, troughcolor=color, highlightthickness=0)
                slider.set(value)
                slider.pack(fill=tk.X, padx=10, pady=0)
                return slider

            tk.Label(color_picker, text="Red").pack(pady=(0, 0))
            red_slider = create_colored_slider(color_picker, "#ff9999", self.crosshair_color[0])

            tk.Label(color_picker, text="Green").pack(pady=(0, 0))
            green_slider = create_colored_slider(color_picker, "#99ff99", self.crosshair_color[1])

            tk.Label(color_picker, text="Blue").pack(pady=(0, 0))
            blue_slider = create_colored_slider(color_picker, "#9999ff", self.crosshair_color[2])

            tk.Label(color_picker, text="Transparency").pack()
            alpha_slider = tk.Scale(color_picker, from_=0, to=255, orient=tk.HORIZONTAL)
            alpha_slider.set(self.crosshair_alpha)
            alpha_slider.pack(fill=tk.X, padx=10, pady=0)
            
            tk.Label(color_picker, text="Additional settings",font=("Arial",12)).pack(pady=(40,10)) 
            red_dot_slider = tk.Scale(color_picker, from_=1, to=50, orient=tk.HORIZONTAL)
            red_dot_slider.set(self.red_dot_radius)
            red_dot_slider.pack(padx=0, pady=200)

            thickness_slider = tk.Scale(color_picker, from_=1, to=10, orient=tk.HORIZONTAL)
            thickness_slider.set(self.crosshair_thickness)
            thickness_slider.pack(padx=10, pady=0)

            def update_red_dot_slider_visibility(*args):
                if type_var.get() == "red_dot":
                    red_dot_slider.pack(pady=0)
                else:
                    red_dot_slider.pack_forget()

            def update_thickness_slider_visibility(*args):
                if type_var.get() == "cross":
                    thickness_slider.pack(pady=0)
                else:
                    thickness_slider.pack_forget()

            def update_settings(event=None):
                self.crosshair_color = (red_slider.get(), green_slider.get(), blue_slider.get())
                self.circle_radius = size_slider.get()
                self.crosshair_alpha = alpha_slider.get()
                self.crosshair_type = type_var.get()
                if self.crosshair_type == "red_dot":
                    self.red_dot_radius = red_dot_slider.get()
                if self.crosshair_type == "cross":
                    self.crosshair_thickness = thickness_slider.get()
                self.update_crosshair()
                update_red_dot_slider_visibility()
                update_thickness_slider_visibility()

            def reset_sliders():
                size_slider.set(3)
                red_slider.set(255)
                green_slider.set(0)
                blue_slider.set(0)
                alpha_slider.set(255)
                type_var.set("circle")
                red_dot_slider.set(5)
                thickness_slider.set(3)
                update_settings()

            red_slider.bind("<Motion>", update_settings)
            green_slider.bind("<Motion>", update_settings)
            blue_slider.bind("<Motion>", update_settings)
            size_slider.bind("<Motion>", update_settings)
            alpha_slider.bind("<Motion>", update_settings)
            red_dot_slider.bind("<Motion>", update_settings)
            thickness_slider.bind("<Motion>", update_settings)
            type_var.trace("w", lambda name, index, mode: update_settings())

            self.move_button = tk.Button(color_picker, text="Move Crosshair", command=self.toggle_move)
            self.move_button.pack(padx=10, pady=5)
            self.move_button.bind("<Button-1>", update_settings)
            tk.Button(color_picker, text="Center Crosshair", command=self.center_crosshair).pack(pady=10)
            tk.Button(color_picker, text="Load Crosshair Image", command=self.load_crosshair_image).pack(pady=5)
            tk.Button(color_picker, text="Restore Default Crosshair", command=lambda: [self.restore_default_crosshair(), reset_sliders()]).pack(pady=20)

            update_red_dot_slider_visibility()
            update_thickness_slider_visibility()

        self.icon = pystray.Icon("Crosshair App", create_image(), menu=pystray.Menu(
                item('Move Crosshair', on_move_crosshair),
                item('Center Crosshair', on_center_crosshair),
                item('Hide/show Crosshair', on_hide),
                item('Configure Crosshair', open_color_picker),
                item('Quit (F9)', on_quit)
            ))

        self.icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        self.icon_thread.start()

    def quit_app(self):
        try:
            if hasattr(self, 'icon'):
                self.icon.stop()
            self.root.quit()
            self.root.destroy()

            if hasattr(self, 'icon_thread'):
                self.icon_thread.join()
        except Exception as e:
            print(f"Error during quit_app: {e}")

    def close(self, event=None):
        self.quit_app()

    def run(self):
        self.root.mainloop()

    def show_startup_image(self):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")

        image_path = os.path.join(base_path, "startup_image.png")

        if os.path.exists(image_path):
            self.startup_image = Image.open(image_path).resize((800, 200))
            draw = ImageDraw.Draw(self.startup_image)
            
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except IOError:
                font = ImageFont.load_default()
            
            text = f"Version: {self.version}"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (self.startup_image.width - text_width) / 2
            text_y = self.startup_image.height - text_height - 10
            draw.text((text_x, text_y), text, font=font, fill="white")

            self.tk_startup_image = ImageTk.PhotoImage(self.startup_image)
            self.canvas.create_image(self.circle_center[0] - 400, self.circle_center[1] - 100, image=self.tk_startup_image, anchor=tk.NW, tags="startup")
            self.root.after(self.startup_duration, self.show_crosshair)
        else:
            self.show_crosshair()

    def show_crosshair(self):
        self.canvas.delete("startup")
        self.update_crosshair()

    def update_crosshair(self):
        if not self.is_visible:
            return

        if self.crosshair_image:
            self.image = self.crosshair_image
            self.image = self.image.resize((self.circle_radius * 2, self.circle_radius * 2), Image.LANCZOS)
            self.image.putalpha(self.crosshair_alpha)
        else:
            self.image = Image.new("RGBA", (self.circle_radius * 2, self.circle_radius * 2), (0, 0, 0, 0))
            self.draw = ImageDraw.Draw(self.image)

            if self.crosshair_type == "circle":
                self.draw.ellipse([
                    0, 0,
                    self.circle_radius * 2, self.circle_radius * 2
                ], fill=self.crosshair_color + (self.crosshair_alpha,))
            elif self.crosshair_type == "cross":
                cross_width = self.crosshair_thickness
                self.draw.line([self.circle_radius, 0, self.circle_radius, self.circle_radius * 2], fill=self.crosshair_color + (self.crosshair_alpha,), width=cross_width)
                self.draw.line([0, self.circle_radius, self.circle_radius * 2, self.circle_radius], fill=self.crosshair_color + (self.crosshair_alpha,), width=cross_width)
            elif self.crosshair_type == "red_dot":
                self.draw.ellipse([0, 0, self.circle_radius * 2, self.circle_radius * 2], outline=self.crosshair_color + (self.crosshair_alpha,), width=2)
                self.draw.ellipse([self.circle_radius - self.red_dot_radius, self.circle_radius - self.red_dot_radius, self.circle_radius + self.red_dot_radius, self.circle_radius + self.red_dot_radius], fill=self.crosshair_color + (self.crosshair_alpha,), outline=self.crosshair_color + (self.crosshair_alpha,))

        self.tk_image = ImageTk.PhotoImage(self.image)

        self.canvas.delete("crosshair")

        self.canvas.create_image(self.circle_center[0] - self.circle_radius, self.circle_center[1] - self.circle_radius, image=self.tk_image, anchor=tk.NW, tags="crosshair")

    def start_move(self, event):
        if self.is_moving:
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def move(self, event):
        if self.is_moving:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            new_center_x = self.circle_center[0] + dx
            new_center_y = self.circle_center[1] + dy

            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            new_center_x = max(self.circle_radius, min(screen_width - self.circle_radius, new_center_x))
            new_center_y = max(self.circle_radius, min(screen_height - self.circle_radius, new_center_y))

            self.circle_center = (new_center_x, new_center_y)
            self.update_crosshair()

    def toggle_move(self):
        self.is_moving = not self.is_moving
        self.update_move_button_text()

    def update_move_button_text(self):
        if hasattr(self, 'move_button'):
            self.move_button.config(text="Lock Crosshair" if self.is_moving else "Move Crosshair")

    def center_crosshair(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.circle_center = (screen_width // 2, screen_height // 2)
        self.update_crosshair()

    def load_crosshair_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            self.crosshair_image_path = file_path
            self.crosshair_image = Image.open(file_path).convert("RGBA")
            self.update_crosshair()

    def restore_default_crosshair(self):
        self.circle_radius = 3
        self.crosshair_color = (255, 0, 0)
        self.crosshair_alpha = 255
        self.crosshair_type = "circle"
        self.red_dot_radius = 5
        self.crosshair_thickness = 3
        self.crosshair_image_path = None
        self.crosshair_image = None
        self.update_crosshair()

if __name__ == "__main__":
    app = CrosshairApp()
    app.run()
