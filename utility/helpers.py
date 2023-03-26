import base64
from io import BytesIO
from PIL import Image

def recolor_image_b64(base64_string, hex_color):
    # Decode the Base64 string to bytes
    decoded_bytes = base64.b64decode(base64_string)

    print(hex_color)

    # Load the image from the decoded bytes
    img = Image.open(BytesIO(decoded_bytes))

    # Convert the hex color to RGB values
    new_color = tuple(int(hex_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # Recolor the image
    img = img.convert("RGBA") # Convert the image to RGBA mode
    data = img.getdata() # Get the pixel data
    new_data = []
    for item in data:
        if item[3] == 0: # If the pixel is transparent, leave it unchanged
            new_data.append(item)
        else:
            new_data.append(new_color) # Change the color of non-transparent pixels
    img.putdata(new_data) # Update the pixel data

    # Convert the image back to Base64
    buffer = BytesIO()
    img.save(buffer, format="PNG") # Save the image to a buffer in PNG format
    base64_encoded = base64.b64encode(buffer.getvalue()).decode("utf-8") # Encode the buffer as Base64

    # Return the new Base64 encoded string
    return base64_encoded