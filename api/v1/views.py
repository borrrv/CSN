import datetime as dt

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import IntegerField, Q, Value
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from djoser.serializers import TokenCreateSerializer, TokenSerializer
from djoser.utils import ActionViewMixin, login_user
from djoser.views import TokenDestroyView
from drf_yasg.utils import swagger_auto_schema
from rest_framework import (filters, generics, permissions, serializers,
                            status, viewsets)
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from posts.models import Comment, Group, Post
from users.models import CustomUser

from .mixins import CreateViewSet, UpdateListRetrieveViewSet
from .permissions import IsAuthorOrReadOnly, IsUserOrReadOnly
from .serializers import (AddressBookSerializer, BirthdaySerializer,
                          ChangePasswordSerializer, CommentSerializer,
                          CreateCustomUserSerializer, GroupSerializer,
                          PostSerializer, ResponseCreateCustomUserSerializer,
                          ShortInfoSerializer, UserSerializer,
                          UserUpdateSerializer)
from .utils import del_files, del_images


class UserPostsViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CustomUser.objects.none()
        user = get_object_or_404(CustomUser, id=self.kwargs.get('user_id'))
        return Post.objects.filter(author=user)


class PostViewSet(viewsets.ModelViewSet):
    """Добавление, изменение и удаление постов. Получение списка постов."""

    queryset = Post.objects.all().prefetch_related('comments')
    serializer_class = PostSerializer
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        del_images(instance)
        del_files(instance)
        super().perform_destroy(instance)

    @action(
        url_path='like',
        methods=('POST',),
        detail=True,
    )
    def set_like(self, request, pk):
        """Лайкнуть пост, отменить лайк."""
        post = get_object_or_404(Post, id=pk)
        post.likes.add(request.user)
        serializer = PostSerializer(post)
        return Response(
            data=serializer.data, status=status.HTTP_201_CREATED
        )

    @set_like.mapping.delete
    def delete_like(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        post.likes.remove(request.user)
        serializer = PostSerializer(post)
        return Response(
            data=serializer.data, status=status.HTTP_200_OK
        )


class CommentsViewSet(ModelViewSet):
    queryset = Comment.objects.all().select_related(
        'author', 'post').prefetch_related('like')
    serializer_class = CommentSerializer
    pagination_class = None
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def get_news(self):
        return get_object_or_404(Post, pk=self.kwargs.get('posts_id'))

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comment.objects.none()
        return self.get_news().comments.all().select_related(
            'author', 'post').prefetch_related('like')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, post=self.get_news())

    @action(
        url_path='like',
        methods=('POST',),
        detail=True,
    )
    def set_like(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, id=self.kwargs['pk'])
        comment.like.add(request.user)
        return Response(
            CommentSerializer(comment).data, status=status.HTTP_201_CREATED
        )

    @set_like.mapping.delete
    def delete_like(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, id=self.kwargs['pk'])
        comment.like.remove(request.user)
        serializer = CommentSerializer(comment)
        return Response(
            data=serializer.data, status=status.HTTP_200_OK
        )


class ChangePasswordView(CreateAPIView):
    """Change password view."""

    serializer_class = ChangePasswordSerializer
    model = CustomUser
    permission_classes = (IsAuthenticated,)

    def get_object(self, queryset=None):
        return self.request.user

    @swagger_auto_schema(responses={200: 'Password updated successfully'})
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            if not self.object.check_password(
                    serializer.validated_data.get('current_password')
            ):
                return Response(
                    {_('current_password'): _('Wrong password.')},
                    status=status.HTTP_400_BAD_REQUEST)
            new_password = serializer.validated_data.get('new_password')
            self.object.set_password(new_password)
            try:
                validate_password(password=new_password, user=self.object)
            except ValidationError as err:
                raise serializers.ValidationError({'password': err.messages})
            self.object.save()
            return Response(
                {_('message'): _('Password updated successfully')},
                status=status.HTTP_200_OK)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class UsersViewSet(UpdateListRetrieveViewSet):
    """Users view."""

    actions_list = ['PATCH']
    queryset = CustomUser.objects.all().prefetch_related('followings')
    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.request.method in self.actions_list:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.request.method in self.actions_list:
            permission_classes = (IsUserOrReadOnly,)
        else:
            permission_classes = (permissions.IsAuthenticated,)
        return [permission() for permission in permission_classes]

    @action(
        methods=('GET',),
        pagination_class=None,
        detail=False
    )
    def me(self, request):
        user_instance = self.request.user
        serializer = self.get_serializer(user_instance)
        return Response(serializer.data, status.HTTP_200_OK)


class CreateUsersViewSet(CreateViewSet):
    """Create users view."""

    queryset = CustomUser.objects.all()
    serializer_class = CreateCustomUserSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(responses={201: ResponseCreateCustomUserSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class GroupViewSet(ReadOnlyModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ('title',)

    @action(
        url_path='subscribe',
        methods=('POST',),
        detail=True,
    )
    def set_subscribe(self, request, pk):
        group = get_object_or_404(Group, id=pk)
        group.followers.add(request.user)
        return Response(
            GroupSerializer(group).data, status=status.HTTP_201_CREATED
        )

    @set_subscribe.mapping.delete
    def delete_subscribe(self, request, pk):
        group = get_object_or_404(Group, id=pk)
        group.followers.remove(request.user)
        return Response(
            GroupSerializer(group).data, status=status.HTTP_200_OK
        )


class ShortInfoView(viewsets.ReadOnlyModelViewSet):
    """Short info about user."""

    serializer_class = ShortInfoSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        return CustomUser.objects.filter(id=user_id).annotate(
            posts_count=Value(
                Post.objects.filter(author_id=user_id).count(),
                output_field=IntegerField())
        )


class BirthdayList(ListAPIView):
    """Сериалайзер для дней рождения"""
    serializer_class = BirthdaySerializer
    pagination_class = None

    def get_queryset(self):
        today = dt.datetime.today().date()
        max_day = today + dt.timedelta(days=3)
        if max_day.month != today.month:
            return (CustomUser.objects.filter(
                Q(birthday_date__month=max_day.month,
                  birthday_date__day__lte=max_day.day)
                | (Q(birthday_date__month=today.month,
                   birthday_date__day__gte=today.day))
            )).order_by('birthday_date__month', 'birthday_date__day')
        return (CustomUser.objects.filter(
            Q(birthday_date__month=today.month,
              birthday_date__day__lte=max_day.day,
              birthday_date__day__gte=today.day)
        )).order_by('birthday_date__month', 'birthday_date__day')


class AddressBookView(ListAPIView):
    """Create address book view."""

    queryset = CustomUser.objects.all().order_by('last_name', 'id')
    serializer_class = AddressBookSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['last_name', 'job_title']


class СhangedActionViewMixin(ActionViewMixin):

    @swagger_auto_schema(responses={200: TokenSerializer})
    def post(self, request, **kwargs):
        return super().post(request)


class TokenCreateView(СhangedActionViewMixin, generics.GenericAPIView):

    serializer_class = TokenCreateSerializer
    permission_classes = (AllowAny,)

    def _action(self, serializer):
        token = login_user(self.request, serializer.user)
        token_serializer_class = TokenSerializer
        return Response(
            data=token_serializer_class(token).data, status=status.HTTP_200_OK
        )


class СhangedTokenDestroyView(TokenDestroyView):

    @swagger_auto_schema(responses={204: ''})
    def post(self, request):
        return super().post(request)
