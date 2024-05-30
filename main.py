from pathlib import Path
import folium
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from exif import Image
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image as PILImage, ImageTk

# Function to read EXIF data from a photo
def read_exif_data(file_path: Path) -> Image:
    """Read metadata from photo."""
    with open(file_path, 'rb') as f:
        return Image(f)

# Function to convert GPS coordinates to decimal format
def convert_coords_to_decimal(coords: tuple[float, ...], ref: str) -> float:
    if ref.upper() in ['W', 'S']:
        mul = -1
    elif ref.upper() in ['E', 'N']:
        mul = 1
    else:
        print("Incorrect hemisphere reference. "
              "Expecting one of 'N', 'S', 'E' or 'W', "
              f'got {ref} instead.')
        
    return mul * (coords[0] + coords[1] / 60 + coords[2] / 3600)  

# Function to extract decimal GPS coordinates from EXIF data
def get_decimal_coord_from_exif(exif_data: Image) -> tuple[float, ...]:
    try:
        lat = convert_coords_to_decimal(
            exif_data['gps_latitude'], 
            exif_data['gps_latitude_ref']
            )
        lon = convert_coords_to_decimal(
            exif_data['gps_longitude'], 
            exif_data['gps_longitude_ref']
            )
        alt = exif_data['gps_altitude']
        return (lat, lon, alt)
    except (AttributeError, KeyError):
        print('Image does not contain spatial data or data is invalid.')  
        raise

# Function to read spatial data from a folder containing images
def read_spatial_data_from_folder(folder: Path, image_extension: str = '*.jpg') -> dict[str, dict]:
    coord_dict = dict()
    source_files = [f for f in folder.rglob(image_extension)]
    exif = [read_exif_data(f) for f in source_files]
    
    for f, data in zip(source_files, exif):
        try:
            coord = get_decimal_coord_from_exif(data)
        except (AttributeError, KeyError):
            continue
        else:
            coord_dict[str(f)] = dict()
            coord_dict[str(f)]['latitude'] = coord[0]
            coord_dict[str(f)]['longitude'] = coord[1]
            coord_dict[str(f)]['altitude'] = coord[2]
            coord_dict[str(f)]['filepath'] = str(f.resolve())
        try:
            coord_dict[str(f)]['timestamp'] = data.datetime
        except (AttributeError, KeyError):
            print(f"Photo {f.name} does not contain datetime information.")
            coord_dict[str(f)]['timestamp'] = None
    
    return coord_dict

# Function to convert RGBA color to hexadecimal
def rgba_to_hex(rgba: tuple[float, ...]):
    return ('#{:02X}{:02X}{:02X}').format(*rgba[:3])

# Function to generate the map using Folium
def generate_map():
    BASE_LOC = Path('images')
    res = read_spatial_data_from_folder(BASE_LOC)
    
    # create dataframe from extracted data
    df = pd.DataFrame(res).T
    df['timestamp'] = pd.to_datetime(df.timestamp, format="%Y:%m:%d %H:%M:%S")
    df.sort_values('timestamp', inplace=True)

    # get colour map
    cmap = plt.get_cmap('plasma')
    norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
    df['color_mapping'] = np.linspace(0, 1, num=df.shape[0])

    sw = (df.latitude.max() + 3, df.longitude.min() - 3)
    ne = (df.latitude.min() - 3, df.longitude.max() + 3)

    m = folium.Map()

    # Add markers
    for lat, lon, col, date, filepath in zip(df.latitude.values, 
                                             df.longitude.values, 
                                             df.color_mapping.values, 
                                             df.timestamp.values,
                                             df.filepath.values):
        photo_url = Path(filepath).as_uri()
        tooltip_content = f"""
        <div style="width: 200px;">
            <img src="{photo_url}" alt="photo" style="width: 100%;"/>
            <p>{np.datetime_as_string(date, unit='m')}</p>
        </div>
        """
        folium.CircleMarker(
            [lat, lon], 
            color=rgba_to_hex(cmap(col, bytes=True)), 
            fill_color=rgba_to_hex(cmap(col, bytes=True)),
            radius=6,
            tooltip=folium.Tooltip(tooltip_content, sticky=True)
        ).add_to(m)

    m.fit_bounds([sw, ne])

    # Save the map to an HTML file
    map_file = Path('map.html').resolve()
    m.save(map_file)
    return map_file

# Function to open the generated map in the default web browser
def open_map():
    map_file = generate_map()
    webbrowser.open(map_file.as_uri())

# Function to handle image upload
def upload_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg")])
    if file_path:
        try:
            dest_path = Path("images") / Path(file_path).name
            Path(file_path).replace(dest_path)
            generate_map()
        except Exception as e:
            messagebox.showerror("Upload Error", "An error occurred during upload. Please ensure you are uploading a valid .jpg image.")

if __name__ == "__main__":
    # Create a Tkinter window
    root = tk.Tk()
    root.title("Photo2Map")
    root.geometry("600x400") 

    # Create a frame for the logo
    top_frame = ttk.Frame(root)
    top_frame.pack(pady=20)

    # Add a logo 
    try:
        logo_image = PILImage.open("Photo2Map.png")
        logo_image = logo_image.resize((100, 100), PILImage.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_image)
        logo_label = ttk.Label(top_frame, image=logo_photo)
        logo_label.pack(side=tk.LEFT, padx=20)
    except FileNotFoundError:
        logo_label = ttk.Label(top_frame, text="Logo")
        logo_label.pack(side=tk.LEFT, padx=20)

    # Create buttons
    upload_button = ttk.Button(root, text="Upload Image", command=upload_image)
    upload_button.pack(pady=10)
    open_button = ttk.Button(root, text="Open Map", command=open_map)
    open_button.pack(pady=10)

    # Start the Tkinter event loop
    root.mainloop()