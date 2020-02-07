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

import os

import nibabel as nib
import torch
from ignite.engine import Events

from monai.data.writers.niftiwriter import write_nifti


class SegmentationSaver:
    """
    Event handler triggered on completing every iteration to save the segmentation predictions.
    """

    def __init__(self, output_path='./', dtype='float32', output_postfix='seg', output_ext='.nii.gz'):
        self.output_path = output_path
        self.dtype = dtype
        self.output_postfix = output_postfix
        self.output_ext = output_ext

    def attach(self, engine):
        return engine.add_event_handler(Events.ITERATION_COMPLETED, self)

    @staticmethod
    def _create_file_basename(postfix, input_file_name, folder_path, data_root_dir=""):
        """
        Utility function to create the path to the output file based on the input
        filename (extension is added by lib level writer before writing the file)

        Args:
            postfix (str): output name's postfix
            input_file_name (str): path to the input image file
            folder_path (str): path for the output file
            data_root_dir (str): if not empty, it specifies the beginning parts of the input file's
          absolute path. This is used to compute `input_file_rel_path`, the relative path to the file from
          `data_root_dir` to preserve folder structure when saving in case there are files in different
          folders with the same file names.
        """

        # get the filename and directory
        filedir, filename = os.path.split(input_file_name)

        # jettison the extension to have just filename
        filename, ext = os.path.splitext(filename)
        while ext != "":
            filename, ext = os.path.splitext(filename)

        # use data_root_dir to find relative path to file
        filedir_rel_path = ""
        if data_root_dir:
            filedir_rel_path = os.path.relpath(filedir, data_root_dir)

        # sub-folder path will be original name without the extension
        subfolder_path = os.path.join(folder_path, filedir_rel_path, filename)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)

        # add the sub-folder plus the postfix name to become the file basename in the output path
        return os.path.join(subfolder_path, filename + "_" + postfix)

    def __call__(self, engine):
        """
        This method assumes:
            - 3rd output of engine.state.batch is a meta data dict
            - engine.state.output is already post-processed and ready for saving as a Nifti1Image.
        """
        meta_data = engine.state.batch[2]  # assuming 3rd output of input dataset is a meta data dict
        filenames = meta_data['filename_or_obj']
        for batch_id, filename in enumerate(filenames):  # save a batch of files
            seg_output = engine.state.output[batch_id]
            if isinstance(seg_output, torch.Tensor):
                seg_output = seg_output.detach().cpu().numpy()
            original_affine = nib.load(filename).affine
            output_filename = self._create_file_basename(self.output_postfix, filename, self.output_path)
            output_filename = '{}{}'.format(output_filename, self.output_ext)
            write_nifti(seg_output, original_affine, output_filename, revert_canonical=True, dtype=seg_output.dtype)
            print('saved: {}'.format(output_filename))