# Copyright 2020 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import PIL
from PIL.GifImagePlugin import Image as GifImage
from tensorboard.compat.proto import summary_pb2


def _image3_animated_gif(imp, scale_factor=1):
    """
    Function to actually create the animated gif.
    Args:
        imp: tuple of tag and a list of image tensors
        scale_factor: amount to multiply values by (if the image data is between 0 and 1, using 255 for this value will
        scale it to displayable range)
    """

    # x=numpy.random.randint(0,256,[10,10,10],numpy.uint8)
    (tag, ims) = imp
    ims = [
        (np.asarray((ims[i, :, :])) * scale_factor).astype(np.uint8)
        for i in range(ims.shape[0])
    ]
    ims = [GifImage.fromarray(im) for im in ims]
    img_str = b''
    for b_data in PIL.GifImagePlugin.getheader(ims[0])[0]:
        img_str += b_data
    img_str += b'\x21\xFF\x0B\x4E\x45\x54\x53\x43\x41\x50' \
               b'\x45\x32\x2E\x30\x03\x01\x00\x00\x00'
    for i in ims:
        for b_data in PIL.GifImagePlugin.getdata(i):
            img_str += b_data
    img_str += b'\x3B'
    summary_image_str = summary_pb2.Summary.Image(
        height=10, width=10, colorspace=1, encoded_image_string=img_str)
    image_summary = summary_pb2.Summary.Value(tag=tag, image=summary_image_str)
    return summary_pb2.Summary(value=[image_summary])


def make_animated_gif_summary(tag,
                              tensor,
                              max_out=3,
                              animation_axes=(1,),
                              image_axes=(2, 3),
                              other_indices=None,
                              scale_factor=1):
    """
    Creates an animated gif out of an image tensor and returns Summary.

    Args:
        tag: Data identifier
        tensor: tensor for the image, expected to be in CDHW format
        max_out: maximum number of slices to animate through
        animation_axes: axis to animate on (not currently used)
        image_axes: axes of image (not currently used)
        other_indices: (not currently used)
        scale_factor: amount to multiply values by (if the image data is between 0 and 1, using 255 for this value will
        scale it to displayable range)
    """

    if max_out == 1:
        suffix = '/image'
    else:
        suffix = '/image/{}'
    if other_indices is None:
        other_indices = {}
    axis_order = [0] + animation_axes + image_axes

    slicing = []
    for i in range(len(tensor.shape)):
        if i in axis_order:
            slicing.append(slice(None))
        else:
            other_ind = other_indices.get(i, 0)
            slicing.append(slice(other_ind, other_ind + 1))
    tensor = tensor[tuple(slicing)]

    for it_i in range(min(max_out, list(tensor.shape)[0])):
        inp = [
            tag + suffix.format(it_i), tensor[it_i, :, :, :]
        ]
        summary_op = _image3_animated_gif(inp, scale_factor)
    return summary_op


def add_animated_gif(writer, tag, image_tensor, max_out, scale_factor, global_step=None):
    """
    Creates an animated gif out of an image tensor and writes it with SummaryWriter.

    Args:
        writer: Tensorboard SummaryWriter to write to
        tag: Data identifier
        image_tensor: tensor for the image to add, expected to be in CDHW format
        max_out: maximum number of slices to animate through
        scale_factor: amount to multiply values by (if the image data is between 0 and 1, using 255 for this value will
        scale it to displayable range)
        global_step: Global step value to record
    """
    writer._get_file_writer().add_summary(make_animated_gif_summary(tag, image_tensor, max_out=max_out,
                                                                    animation_axes=[1], image_axes=[2, 3],
                                                                    scale_factor=scale_factor), global_step)


def add_animated_gif_no_channels(writer, tag, image_tensor, max_out, scale_factor, global_step=None):
    """
    Creates an animated gif out of an image tensor and writes it with SummaryWriter.

    Args:
        writer: Tensorboard SummaryWriter to write to
        tag: Data identifier
        image_tensor: tensor for the image to add, expected to be in DHW format
        max_out: maximum number of slices to animate through
        scale_factor: amount to multiply values by (if the image data is between 0 and 1, using 255 for this value will
        scale it to displayable range)
        global_step: Global step value to record
    """
    writer._get_file_writer().add_summary(make_animated_gif_summary(tag, image_tensor.unsqueeze(0),
                                                                    max_out=max_out, animation_axes=[1],
                                                                    image_axes=[2, 3], scale_factor=scale_factor),
                                          global_step)
