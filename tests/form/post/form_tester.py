from io import BytesIO
from typing import Type, Dict

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import BaseForm

from adapters.post import PostModelAdapter
from form.base_form_tester import BaseFormTester


class PostFormTester(BaseFormTester):
    @property
    def has_textarea(self):
        return True

    @staticmethod
    def init_create_item_form(Form: Type[BaseForm], **form_data) -> BaseForm:
        image_data = BytesIO()
        Image.new("RGB", (100, 100)).save(image_data, "JPEG")
        image_data.seek(0)
        from blog.models import Post

        files = {
            PostModelAdapter(Post).get_student_field_name(
                "image"
            ): SimpleUploadedFile(
                "test_image.jpg", image_data.read(), content_type="image/jpeg"
            ),
        }

        result = Form(data=form_data, files=files)
        return result

    @staticmethod
    def generate_files_dict() -> Dict[str, SimpleUploadedFile]:
        image_data = BytesIO()
        Image.new("RGB", (100, 100)).save(image_data, "JPEG")
        image_data.seek(0)
        from blog.models import Post

        files = {
            PostModelAdapter(Post).get_student_field_name(
                "image"
            ): SimpleUploadedFile(
                "test_image.jpg", image_data.read(), content_type="image/jpeg"
            ),
        }
        return files
