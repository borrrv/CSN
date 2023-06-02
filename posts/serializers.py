from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from posts.models import Image, Post
from posts.utils import del_images
from users.serializers import UserSerializer


class ImageSerializer(serializers.ModelSerializer):
    """Сериализация изображений."""

    image_link = Base64ImageField(required=False)

    class Meta:
        fields = ('image_link',)
        model = Image


class PostSerializer(serializers.ModelSerializer):
    """Сериализация модели Post."""

    author = UserSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    images = ImageSerializer(many=True, required=False)

    class Meta:
        fields = (
            'id', 'text', 'author', 'pub_date',
            'update_date', 'images', 'like_count'
        )
        model = Post

    def get_like_count(self, obj_post):
        """Вычисляет количество лайков у поста."""
        return obj_post.users_like.count()

    @staticmethod
    def create_images(images, post):
        """Сохраняет картинки к посту."""
        objs_image = (
            Image(
                post=post,
                image_link=image.get('image_link')
            ) for image in images
        )
        Image.objects.bulk_create(objs_image)

    @transaction.atomic
    def create(self, validate_data):
        images = validate_data.pop('images')
        post = Post(**validate_data)
        post.save()
        self.create_images(images, post)
        return post

    @transaction.atomic()
    def update(self, instance, validate_data):
        images = validate_data.pop('images')
        super().update(instance, validate_data)
        del_images(instance)
        Image.objects.filter(post=instance).delete()
        self.create_images(images, instance)
        return instance