import streamlit as st
from PIL import Image
import io
import zipfile
from cairosvg import svg2png  # For SVG to PNG conversion
import os

st.title("🖼️ Batch Image Format Converter & Resizer")

# File upload section with multiple files allowed
uploaded_files = st.file_uploader(
    "Upload images (up to 100)", 
    type=["jpg", "jpeg", "png", "webp", "eps", "svg", "tif", "tiff", "psd"], 
    accept_multiple_files=True
)

# Check if the number of uploaded files exceeds the limit
if uploaded_files and len(uploaded_files) > 100:
    st.error("You can upload a maximum of 100 files at a time.")
    st.stop()

# Conversion settings
target_format = st.selectbox("Select target format", ["JPEG", "PNG", "WebP", "SVG"]).lower()
resize_option = st.radio("Resize options:", ("Original Size", "Custom Dimensions", "Scale Percentage"))

# Resize parameters
new_width, new_height = None, None
scale_percent = 100

if resize_option == "Custom Dimensions":
    if uploaded_files:
        new_width = st.number_input("Width (pixels)", min_value=1, value=500)
        new_height = st.number_input("Height (pixels)", min_value=1, value=500)
elif resize_option == "Scale Percentage":
    scale_percent = st.number_input("Scale percentage", min_value=1, max_value=500, value=100)

# File size management
max_size_option = st.checkbox("Set maximum file size")
max_size_bytes = None
if max_size_option:
    max_size_mb = st.number_input("Maximum file size (MB)", min_value=0.1, value=1.0, step=0.1)
    max_size_bytes = max_size_mb * 1024 * 1024

if st.button("Process and Download All"):
    if uploaded_files:
        # Create a ZIP file to store all processed images
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
            progress_bar = st.progress(0)  # Initialize progress bar
            total_files = len(uploaded_files)
            
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    # Open the image
                    image = Image.open(uploaded_file)
                    
                    # Handle transparency for JPEG format
                    if target_format in ["jpeg", "jpg"] and image.mode in ['RGBA', 'LA']:
                        image = image.convert('RGB')
                    
                    # Resize image based on user selection
                    if resize_option == "Custom Dimensions":
                        image = image.resize((new_width, new_height))
                    elif resize_option == "Scale Percentage":
                        width, height = image.size
                        new_width = int(width * scale_percent / 100)
                        new_height = int(height * scale_percent / 100)
                        image = image.resize((new_width, new_height))

                    # Initialize conversion parameters
                    img_buffer = io.BytesIO()
                    params = {'format': target_format}
                    
                    # Set format-specific parameters
                    if target_format in ["jpeg", "jpg"]:
                        params['quality'] = 95  # Start with high quality
                    elif target_format == "png":
                        params['compress_level'] = 9  # Max compression
                    elif target_format == "webp":
                        params['quality'] = 80

                    # Handle SVG conversion
                    if uploaded_file.type in ["image/svg+xml"] and target_format in ["png", "jpeg", "jpg"]:
                        svg_data = uploaded_file.read()
                        if target_format == "png":
                            img_buffer = io.BytesIO()
                            svg2png(bytestring=svg_data, write_to=img_buffer)
                        elif target_format in ["jpeg", "jpg"]:
                            img_buffer = io.BytesIO()
                            svg2png(bytestring=svg_data, write_to=img_buffer)
                            image = Image.open(img_buffer).convert("RGB")
                            img_buffer = io.BytesIO()
                            image.save(img_buffer, format="jpeg", quality=95)
                    else:
                        image.save(img_buffer, **params)

                    # Optimize file size if needed
                    current_size = img_buffer.tell()
                    if max_size_bytes and current_size > max_size_bytes:
                        if target_format in ["jpeg", "jpg", "webp"]:
                            quality_param = 'quality'
                            min_quality = 10 if target_format == "webp" else 5
                            current_quality = params.get(quality_param, 95)
                            
                            while current_quality >= min_quality and current_size > max_size_bytes:
                                current_quality -= 5
                                img_buffer = io.BytesIO()
                                image.save(img_buffer, format=target_format, **{quality_param: current_quality})
                                current_size = img_buffer.tell()
                            
                            if current_quality < min_quality:
                                st.warning(f"Reached minimum quality settings for {uploaded_file.name}. File size might still exceed limit.")
                        elif target_format == "png":
                            st.warning(f"PNG uses maximum compression for {uploaded_file.name}. Further size reduction requires resizing.")

                    # Add processed file to ZIP
                    img_buffer.seek(0)
                    file_name = f"processed_{uploaded_file.name.split('.')[0]}.{target_format}"
                    zip_file.writestr(file_name, img_buffer.read())

                    # Update progress bar
                    progress_bar.progress((i + 1) / total_files)
                
                except Exception as e:
                    st.error(f"Processing error for {uploaded_file.name}: {e}")

        # Provide download link for the ZIP file
        zip_buffer.seek(0)
        st.success("All files processed successfully!")
        st.download_button(
            label="Download All as ZIP",
            data=zip_buffer,
            file_name="processed_images.zip",
            mime="application/zip"
        )
    else:
        st.warning("Please upload at least one image first!")