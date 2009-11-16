def resize_image(fobj, size=(50, 50)):
    import Image
    from StringIO import StringIO
    
    image = Image.open(fobj)
    if image.mode not in ('L', 'RGB'):
        image = image.convert('RGB')
    image = image.resize(size, Image.ANTIALIAS)
    o = StringIO()
    image.save(o, "JPEG")
    o.seek(0)
    return o

def resize_image_string(buf, size=(50, 50)):
    from StringIO import StringIO
    f = StringIO(buf)
    return resize_image(f, size).getvalue()
    
