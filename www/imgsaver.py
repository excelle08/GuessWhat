__author__ = 'Excelle'

import base64
import re
from apis import APIValueError
from core.db import next_id


def parseImage(raw_data):
    header, data = re.split(r',', raw_data, 1)
    img_type, encoding = re.split(r';', header, 1)
    suffix = ''
    filename = next_id()
    if img_type == 'data:image/png':
        suffix = '.png'
    elif img_type == 'data:image/gif':
        suffix = '.gif'
    elif img_type == 'data:image/jpeg':
        suffix = '.jpg'
    else:
        raise APIValueError('image', message='Invalid image type')
    with open('resources/images/uploads/' + filename + suffix,
             'wb') as fp:
        fp.write(base64.decodestring(data))
    return '/resources/images/uploads/' + filename + suffix
