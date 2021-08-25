import os
from datetime import date, timedelta

from GIBSDownloader.product import Product
from GIBSDownloader.coordinate_utils import Rectangle, Coordinate

import rasterio
from rasterio.transform import from_bounds

MAX_JPEG_SIZE = 65500

class TiffDownloader():
    """Class containing several useful methods for downloading regions"""

    @classmethod
    def generate_download_filename(cls, output, name, date):
        """Creates the filename for the `product` download of `date`"""
        return "{}{}_{}".format(output, name, date)

    @classmethod
    def download_area_tiff(cls, region, date, xml_path, filename, name, res, img_format, width=None, height=None):
        """
        Calls the command to download the user's requested region.

        If the image does not exceed the JPEG library's maximum dimension size
        limit, then the image is downloaded in product's
        """
        maxed_jpg = False

        if width is None and height is None:
            width, height = region.calculate_width_height(res)
            if width > MAX_JPEG_SIZE or height > MAX_JPEG_SIZE:
                maxed_jpg = True

        lon_lat = "{l_x} {upper_y} {r_x} {lower_y}".format(l_x=region.bl_coords.x, upper_y=region.tr_coords.y, r_x=region.tr_coords.x, lower_y=region.bl_coords.y)

        xml_filename = TiffDownloader.generate_xml(xml_path, name, date)

        # command = "gdal_translate -of GTiff -outsize {w} {h} -projwin {ll} -co 'TFW=YES' {xml} {f}.{ext}".format(w=width, h=height, ll=lon_lat, xml=xml_filename, f=filename, ext=img_format)
        # command = "gdal_translate -of {of} -outsize {w} {h} -projwin {ll}  {xml} {f}.{ext}".format(of=img_format.upper(), w=width, h=height, ll=lon_lat, xml=xml_filename, f=filename, ext=img_format)

        with rasterio.open(xml_filename) as src:
            wind = src.window(
                region.bl_coords.x,
                region.bl_coords.y,
                region.tr_coords.x,
                region.tr_coords.y,
                precision=21
            )
            profile = src.profile
            if maxed_jpg:
                profile["driver"] = 'GTiff'
                profile["width"] = width
                profile["height"] = height
                if src.crs is not None:
                    profile["transform"] = from_bounds(
                        region.bl_coords.x,
                        region.bl_coords.y,
                        region.tr_coords.x,
                        region.tr_coords.y,
                        width,
                        height,
                    )

                with rasterio.open(filename, "w", **profile, tfw=True) as dst_src:
                    dst_src.write(
                        src.read(window=wind, out_shape=(src.count, height, width))
                    )
            else:
                profile["driver"] = img_format
                profile["width"] = width
                profile["height"] = height
                if src.crs is not None:
                    profile["transform"] = from_bounds(
                        region.bl_coords.x,
                        region.bl_coords.y,
                        region.tr_coords.x,
                        region.tr_coords.y,
                        width,
                        height,
                    )
                with rasterio.open(filename, "w", **profile) as dst_src:
                    dst_src.write(
                        src.read(window=wind, out_shape=(src.count, height, width))
                    )
        # os.system(command)
 

    @classmethod
    def get_dates_range(cls, start_date, end_date):
        """Returns a list dates between `start_date` and `end_date`"""
        start_components = start_date.split('-')
        end_components = end_date.split('-')

        d1 = date(int(start_components[0]), int(start_components[1]), int(start_components[2]))
        d2 = date(int(end_components[0]), int(end_components[1]), int(end_components[2]))

        return [d1 + timedelta(days=x) for x in range((d2 - d1).days + 1)]
    
    @classmethod
    def generate_xml(cls, xml_path, name, date):
        """Generates the xml configuration file necessary for GDAL download"""
        xml_base = '<GDAL_WMS><Service name="TiledWMS"><ServerUrl>https://gibs.earthdata.nasa.gov/twms/epsg4326/best/twms.cgi?'
        xml_end = '</ServerUrl><TiledGroupName>{name} tileset</TiledGroupName><Change key="${{time}}">{date}</Change></Service></GDAL_WMS>'.format(name=name,date=date)
        xml_content = xml_base + xml_end
        xml_filename = '{}{}.xml'.format(xml_path, date)

        with open(xml_filename, 'w') as xml_file:
            xml_file.write(xml_content)
        return xml_filename