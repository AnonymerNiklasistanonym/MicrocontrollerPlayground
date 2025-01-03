# Run this file to test the render method with dummy data

import tkinter as tk
from datetime import datetime, timedelta

from PIL import Image, ImageTk

from lib.render.render import render_display_bw, Action, Widget, Width, Height, ActionContent, WidgetContent


def update_image():
    current_width = root.winfo_width() if root.winfo_width() != 1 else 800
    current_height = root.winfo_height() if root.winfo_height() != 1 else 480

    # Render the updated image
    image = render_display_bw([
        Action(generate_content=lambda: ActionContent((None, None, "Action #1")), date=start_time.date() + timedelta(days=0)),
        Action(generate_content=lambda: ActionContent(("info_white", "[Trash]", "Action #2")), date=start_time.date() + timedelta(days=2))
    ], [
        Widget(generate_content=lambda: [
            WidgetContent(((start_time.date() + timedelta(days=0)).strftime('%d.%m'), "Biomüll")),
            WidgetContent(((start_time.date() + timedelta(days=2)).strftime('%d.%m'), "Restmüll")),
        ]),
        Widget(generate_content=lambda: [WidgetContent(("Temperature", f"{23}°C"))]),
        Widget(generate_content=lambda: [WidgetContent(("Relative Humidity", f"{60}%"))]),
    ], (Width(current_width), Height(current_height)))

    # Ensure the image is valid and update the label
    if isinstance(image, Image.Image):
        # Convert the Pillow image to a Tkinter-compatible format
        new_photo = ImageTk.PhotoImage(image)
        label.config(image=new_photo)
        # keep a reference to the image
        label.image = new_photo
    else:
        raise RuntimeError("Image is not an instance of PIL.Image")

    # Schedule the next update in 10 seconds
    root.after(1000, update_image)


start_time = datetime.now()


if __name__ == '__main__':
    start_time = datetime.now()
    # Create the Tkinter window
    root = tk.Tk()
    root.title("Test render")
    root.geometry('800x480')
    root.resizable(True, True)
    label = tk.Label(root)
    label.pack(fill=tk.BOTH, expand=True)
    root.after(0, update_image)
    # Start the Tkinter event loop
    root.mainloop()
