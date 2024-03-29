import logging

from django.db import models

from users.models import CustomUser

logger = logging.getLogger('django.db.backends')

LIMIT_CHARS = 25


class AbstractBaseModel(models.Model):
    text = models.TextField('Текст', max_length=2000)
    pub_date = models.DateField('Дата создания', auto_now=True)
    update_date = models.DateTimeField(
        verbose_name='Последнее обновление',
        auto_now=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.text[:LIMIT_CHARS]


class Group(models.Model):
    title = models.CharField('Название', max_length=50)
    description = models.CharField('Описание', max_length=1000)
    created_date = models.DateTimeField('Дата создания', auto_now_add=True)
    resume = models.CharField('Резюме', max_length=35)
    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='group',
        blank=True,
    )
    followers = models.ManyToManyField(
        CustomUser,
        verbose_name='Подписчики',
        related_name='followings',
        blank=True,
    )
    image_link = models.ImageField(
        'Изображение',
        upload_to='groups/images/%Y/%m/%d',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ('-created_date', '-id',)

    def __str__(self):
        return self.title[:LIMIT_CHARS]


class Post(AbstractBaseModel):
    """Модель поста."""

    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='posts',
    )
    likes = models.ManyToManyField(
        CustomUser,
        verbose_name='Лайки',
        related_name='posts_liked',
        blank=True
    )
    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        related_name='posts_group',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ('-pub_date', '-id')

    def save(
        self, force_insert=False, force_update=False,
        using=None, update_fields=None
    ):
        is_created = False
        if self.id:
            logger.info(f'Обновление поста id#{self.id} - "{self.text[:50]}"')
        else:
            logger.info(f'Создание поста - "{self.text[:50]}"')
            is_created = True
        super().save(force_insert, force_update, using, update_fields)
        if is_created:
            logger.info(f'Создан пост id#{self.id}')


class Comment(AbstractBaseModel):
    text = models.TextField('Текст', max_length=500)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Пост',
        related_name='comments',
    )
    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    like = models.ManyToManyField(
        CustomUser,
        verbose_name='Лайки',
        related_name='comments_likes',
        blank=True
    )

    class Meta:
        ordering = ('pub_date', 'id')
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'


class Image(models.Model):
    """Модель для изображений к посту."""

    post = models.ForeignKey(
        Post,
        verbose_name='Пост',
        related_name='images',
        on_delete=models.CASCADE,
    )
    image_link = models.ImageField(
        verbose_name='Изображение',
        upload_to='posts/images/%Y/%m/%d',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'
        ordering = ('-post', 'id',)

    def save(
        self, force_insert=False, force_update=False,
        using=None, update_fields=None
    ):
        is_created = False
        if self.id:
            logger.info(
                f'Обновление изображения id#{self.id} к посту "{self.post}"'
            )
        else:
            logger.info(f'Создание изображения к посту "{self.post}"')
            is_created = True
        super().save(force_insert, force_update, using, update_fields)
        if is_created:
            logger.info(f'Создано изображение id#{self.id}')


class File(models.Model):
    """Модель для файлов к посту."""

    post = models.ForeignKey(
        Post,
        verbose_name='Пост',
        related_name='files',
        on_delete=models.CASCADE,
    )
    file_link = models.FileField(
        verbose_name='Файл',
        upload_to='posts/files/%Y/%m/%d',
        blank=True,
        null=True,
    )
    file_title = models.CharField(
        verbose_name='Название',
        max_length=100,
        blank=True
    )

    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'
        ordering = ('-post', 'id',)

    def save(
        self, force_insert=False, force_update=False,
        using=None, update_fields=None
    ):
        is_created = False
        if self.id:
            logger.info(
                f'Обновление файла id#{self.id} к посту "{self.post}"'
            )
        else:
            logger.info(f'Создание файла к посту "{self.post}"')
            is_created = True
        super().save(force_insert, force_update, using, update_fields)
        if is_created:
            logger.info(f'Создан файл id#{self.id}')
