from datetime import datetime

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect

from .forms import PostForm, CommentForm, UserForm
from .models import Post, Category, User, Comment


def posts(**kwargs):
    """Отфильтрованное получение постов из БД"""
    return Post.objects.select_related(
        'category',
        'location',
        'author'
    ).annotate(comment_count=Count('comments')
               ).filter(**kwargs).order_by('-pub_date')


def paginator(request, **kwargs):
    """Представление постов в виде пагинатора, по 10 шт на странице"""
    paginator = Paginator(posts(**kwargs), 10)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    """Главная страница / Лента записей"""
    page_obj = paginator(request,
                         is_published=True,
                         category__is_published=True,
                         pub_date__lte=datetime.now())
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def category_posts(request, category_slug):
    """Отображение публикаций в категории"""
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True)
    page_obj = paginator(request,
                         is_published=True,
                         pub_date__lte=datetime.now(),
                         category=category)
    context = {'category': category,
               'page_obj': page_obj}
    return render(request, 'blog/post_list.html', context)


def post_detail(request, post_id):
    """Отображение полного описания выбранной записи"""
    post = get_object_or_404(posts(), id=post_id)
    comments = Comment.objects.select_related(
        'author',
        'post'
    ).filter(post_id=post_id).order_by('created_at')
    form = CommentForm(request.POST or None)
    context = {'post': post,
               'comments': comments,
               'form': form}
    return render(request, 'blog/post_detail.html', context)


@login_required
def create_post(request):
    """Создание поста"""
    form = PostForm(request.POST or None)
    context = {'form': form}
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:index')
    return render(request, 'blog/create.html', context)


@login_required
def edit_post(request, post_id):
    """Редактирование поста"""
    post = get_object_or_404(posts(), id=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        form = PostForm(request.POST or None, instance=post)
        context = {'form': form}
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id)
        return render(request, 'blog/create.html', context)


@login_required
def delete_post(request, post_id):
    """Удаление поста"""
    post = get_object_or_404(posts(), pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        form = PostForm(request.POST or None, instance=post)
        context = {'form': form}
        if request.method == 'POST':
            post.delete()
            return redirect('blog:index')
        return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    """Добавление комментария"""
    post = get_object_or_404(posts(), pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария"""
    comment = get_object_or_404(Comment, post_id=post_id, id=comment_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        form = CommentForm(request.POST or None, instance=comment)
        context = {'comment': comment,
                   'form': form}
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id)
        return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария"""
    comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        context = {'comment': comment}
        if request.method == 'POST':
            comment.delete()
            return redirect('blog:post_detail', post_id)
        return render(request, 'blog/comment.html', context)


def profile(request, username):
    """Отображение страницы пользователя"""
    profile = get_object_or_404(
        User,
        username=username)
    page_obj = paginator(request,
                         author=profile)
    context = {'profile': profile,
               'page_obj': page_obj}
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request, username):
    """Редактирование страницы пользователя"""
    profile = get_object_or_404(
        User,
        username=username)
    form = UserForm(request.POST or None, instance=profile)
    context = {'form': form}
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username)
    return render(request, 'blog/user.html', context)
