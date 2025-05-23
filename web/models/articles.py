import re
import auto_prefetch

from uuid import uuid4
from django.core.validators import RegexValidator
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

from web.fields import CITextField
from .users import VisualUserGroup
from .settings import Settings
from .site import Site


User = get_user_model()


class TagsCategorySlugValidator(RegexValidator):
    regex = r"^[a-zа-я0-9.-_]+\Z"
    message = "Идентификатор категории тега может содержать только строчные буквы, цифры и символы [.-_] (без скобок)."
    flags = re.ASCII


class TagsCategory(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Категория тегов"
        verbose_name_plural = "Категории тегов"

        constraints = [models.UniqueConstraint(fields=['slug'], name='%(app_label)s_%(class)s_unique')]
        indexes = [models.Index(fields=['name'])]

    name = models.TextField(verbose_name="Полное название")
    description = models.TextField(blank=True, verbose_name="Описание")
    priority = models.PositiveIntegerField(null=True, blank=True, unique=True, verbose_name="Порядковый номер")
    slug = models.TextField(verbose_name="Идентификатор", unique=True, validators=[TagsCategorySlugValidator()])

    def __str__(self):
        return f"{self.name} ({self.slug})"

    @staticmethod
    def get_or_create_default_tags_category():
        category, _ = TagsCategory.objects.get_or_create(slug="_default", defaults=dict(name="Default"))
        return category.pk

    @property
    def is_default(self) -> bool:
        return self.slug == "_default"

    def save(self, *args, **kwargs):
        if not self.id and not self.name:
            self.name = self.slug
        return super(TagsCategory, self).save(*args, **kwargs)


class Tag(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

        constraints = [models.UniqueConstraint(fields=['category', 'name'], name='%(app_label)s_%(class)s_unique')]
        indexes = [models.Index(fields=['category', 'name'])]

    category = auto_prefetch.ForeignKey(TagsCategory, null=False, blank=False, on_delete=models.CASCADE, verbose_name="Категория", default=TagsCategory.get_or_create_default_tags_category)
    name = models.TextField(verbose_name="Название")

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        if self.category and not self.category.is_default:
            return f"{self.category.slug}:{self.name}"
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        return super(Tag, self).save(*args, **kwargs)


class Category(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Настройки категории"
        verbose_name_plural = "Настройки категорий"

        constraints = [models.UniqueConstraint(fields=['name'], name='%(app_label)s_%(class)s_unique')]
        indexes = [models.Index(fields=['name'])]

    name = models.TextField(verbose_name="Имя")

    is_indexed = models.BooleanField(verbose_name='Индексируется поисковиками', null=False, default=True)

    readers_can_view = models.BooleanField(verbose_name='Читатели могут просматривать статьи', null=False, default=True)
    readers_can_create = models.BooleanField(verbose_name='Читатели могут создавать статьи', null=False, default=False)
    readers_can_edit = models.BooleanField(verbose_name='Читатели могут редактировать статьи', null=False, default=False)
    readers_can_rate = models.BooleanField(verbose_name='Читатели могут голосовать за статьи', null=False, default=True)
    readers_can_comment = models.BooleanField(verbose_name='Читатели могут комментировать статьи', null=False, default=True)
    readers_can_delete = models.BooleanField(verbose_name='Читатели могут удалять статьи', null=False, default=False)

    users_can_view = models.BooleanField(verbose_name='Участники могут просматривать статьи', null=False, default=True)
    users_can_create = models.BooleanField(verbose_name='Участники могут создавать статьи', null=False, default=True)
    users_can_edit = models.BooleanField(verbose_name='Участники могут редактировать статьи', null=False, default=True)
    users_can_rate = models.BooleanField(verbose_name='Участники могут голосовать за статьи', null=False, default=True)
    users_can_comment = models.BooleanField(verbose_name='Участники могут комментировать статьи', null=False, default=True)
    users_can_delete = models.BooleanField(verbose_name='Участники могут удалять статьи', null=False, default=False)

    def __str__(self) -> str:
        return self.name

    # this function returns site settings overridden by category settings.
    # if neither is set, falls back to defaults defined in Settings class.
    def get_settings(self):
        category_settings = Settings.objects.filter(category=self).first() or Settings.get_default_settings()
        site_settings = Site.objects.get().get_settings() or Settings.get_default_settings()
        return Settings.get_default_settings().merge(site_settings).merge(category_settings)


class Article(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"

        constraints = [models.UniqueConstraint(fields=['category', 'name'], name='%(app_label)s_%(class)s_unique')]
        indexes = [models.Index(fields=['category', 'name']), models.Index(fields=['created_at']), models.Index(fields=['updated_at'])]

    category = models.TextField(default="_default", verbose_name="Категория")
    name = models.TextField(verbose_name="Имя")
    title = models.TextField(verbose_name="Заголовок")

    parent = auto_prefetch.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Родитель")
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles", verbose_name="Тэги")
    author = auto_prefetch.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Автор")

    locked = models.BooleanField(default=False, verbose_name="Страница защищена")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    updated_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")

    media_name = models.TextField(verbose_name="Название папки с файлами в ФС-хранилище", unique=True, default=uuid4)

    def get_settings(self):
        try:
            category_as_object = Category.objects.get(name__iexact=self.category)
            return category_as_object.get_settings()
        except Category.DoesNotExist:
            site_settings = Site.objects.get().get_settings()
            return Settings.get_default_settings().merge(site_settings)

    @property
    def full_name(self) -> str:
        if self.category != '_default':
            return f"{self.category}:{self.name}"
        return self.name

    @property
    def display_name(self) -> str:
        return self.title.strip() or self.full_name

    def __str__(self) -> str:
        return f"{self.title} ({self.full_name})"


class ArticleVersion(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Версия статьи"
        verbose_name_plural = "Версии статей"

        indexes = [models.Index(fields=['article', 'created_at'])]

    article = auto_prefetch.ForeignKey(Article, on_delete=models.CASCADE, verbose_name="Статья", related_name='versions')
    source = models.TextField(verbose_name="Исходник")
    ast = models.JSONField(blank=True, null=True, verbose_name="AST-дерево статьи")
    rendered = models.TextField(blank=True, null=True, verbose_name="Рендер статьи")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")

    def __str__(self) -> str:
        return f"{self.created_at.strftime('%Y-%m-%d, %H:%M:%S')} - {self.article}"


class ArticleLogEntry(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Запись в журнале изменений"
        verbose_name_plural = "Записи в журнале изменений"

        constraints = [models.UniqueConstraint(fields=['article', 'rev_number'], name='%(app_label)s_%(class)s_unique')]

    class LogEntryType(models.TextChoices):
        Source = ('source', 'Изменение содержимого')
        Title = ('title', 'Изменение заголовка')
        Name = ('name', 'Изменение адреса страницы')
        Tags = ('tags', 'Изменение тегов')
        New = ('new', 'Создание страницы')
        Parent = ('parent', 'Изменение родителя')
        FileAdded = ('file_added', 'Добавление файлов')
        FileDeleted = ('file_deleted', 'Удаление файлов')
        FileRenamed = ('file_renamed', 'Переименование файлов')
        VotesDeleted = ('votes_deleted', 'Сброс рейтинга')
        Wikidot = ('wikidot', 'Правка с Wikidot')
        Revert = ('revert', 'Откат правки')

    article = auto_prefetch.ForeignKey(Article, on_delete=models.CASCADE, verbose_name="Статья")
    user = auto_prefetch.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Пользователь")
    type = models.TextField(choices=LogEntryType.choices, verbose_name="Тип")
    meta = models.JSONField(default=dict, blank=True, verbose_name="Мета")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    rev_number = models.PositiveIntegerField(verbose_name="Номер правки")

    def __str__(self) -> str:
        return f"№{self.rev_number} - {self.article}"


class Vote(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"

        constraints = [models.UniqueConstraint(fields=['article', 'user'], name='%(app_label)s_%(class)s_unique')]
        indexes = [models.Index(fields=['article'])]

    article = auto_prefetch.ForeignKey(Article, on_delete=models.CASCADE, verbose_name="Статья", related_name='votes')
    user = auto_prefetch.ForeignKey(User, null=True, on_delete=models.SET_NULL, verbose_name="Пользователь")
    rate = models.FloatField(verbose_name="Оценка")
    date = models.DateTimeField(verbose_name="Дата голоса", auto_now_add=True, null=True)
    visual_group = auto_prefetch.ForeignKey(VisualUserGroup, on_delete=models.SET_NULL, verbose_name="Визуальная группа", null=True)

    def __str__(self) -> str:
        return f"{self.article}: {self.user} - {self.rate}"


class ExternalLink(auto_prefetch.Model):
    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Связь"
        verbose_name_plural = "Связи"

        indexes = [
            models.Index(fields=['link_from', 'link_to']),
            models.Index(fields=['link_type'])
        ]

        constraints = [models.UniqueConstraint(fields=['link_from', 'link_to', 'link_type'], name='%(app_label)s_%(class)s_unique')]

    class Type(models.TextChoices):
        Include = 'include'
        Link = 'link'

    link_from = CITextField(verbose_name="Ссылающаяся статья", null=False)
    link_to = CITextField(verbose_name="Целевая статья", null=False)
    link_type = models.TextField(choices=Type.choices, verbose_name="Тип ссылки", null=False)
