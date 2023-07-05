from datetime import datetime

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect

from .forms import PostForm, CommentForm, UserForm
from .models import Post, Category, User, Comment


def get_posts(**kwargs):
    """Отфильтрованное получение постов из БД"""
    return Post.objects.select_related(
        'category',
        'location',
        'author'
    ).annotate(comment_count=Count('comments')
               ).filter(**kwargs).order_by('-pub_date')


def get_paginator(request, **kwargs):
    """Отфильтрованное представление постов в виде пагинатора,
       по 10 шт на странице"""
    paginator = Paginator(get_posts(**kwargs), 10)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_author(lst, **kwargs):
    """Получение автора публикации/комментария"""
    return get_object_or_404(lst, **kwargs).author


def index(request):
    """Главная страница / Лента публикаций"""
    page_obj = get_paginator(request,
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
    page_obj = get_paginator(request,
                             is_published=True,
                             category__is_published=True,
                             pub_date__lte=datetime.now(),
                             category=category)
    context = {'category': category,
               'page_obj': page_obj}
    return render(request, 'blog/post_list.html', context)


def post_detail(request, post_id):
    """Отображение полного описания выбранной публикации"""
    author = get_author(get_posts(), id=post_id)
    if author == request.user:
        post = get_object_or_404(get_posts(), id=post_id)
    else:
        post = get_object_or_404(get_posts(
            is_published=True,
            category__is_published=True,
            pub_date__lte=datetime.now()), id=post_id)
    form = CommentForm(request.POST or None)
    comments = Comment.objects.select_related(
        'author',
        'post'
    ).filter(post_id=post_id).order_by('created_at')
    context = {'post': post,
               'form': form,
               'comments': comments}
    return render(request, 'blog/post_detail.html', context)


@login_required
def create_post(request):
    """Создание публикации"""
    form = PostForm(request.POST or None, files=request.FILES or None)
    context = {'form': form}
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user)
    return render(request, 'blog/create.html', context)


@login_required
def edit_post(request, post_id):
    """Редактирование публикации"""
    author = get_author(get_posts(), id=post_id)
    if author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        post = get_object_or_404(get_posts(), id=post_id)
        form = PostForm(request.POST or None, instance=post)
        context = {'form': form}
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id)
        return render(request, 'blog/create.html', context)


@login_required
def delete_post(request, post_id):
    """Удаление публикации"""
    author = get_author(get_posts(), id=post_id)
    if author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        post = get_object_or_404(get_posts(), id=post_id)
        form = PostForm(request.POST or None, instance=post)
        context = {'form': form}
        if request.method == 'POST':
            post.delete()
            return redirect('blog:index')
        return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    """Добавление комментария к публикации"""
    post = get_object_or_404(get_posts(), pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария к публикации"""
    author = get_author(Comment, post_id=post_id, id=comment_id)
    if author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        comment = get_object_or_404(Comment, post_id=post_id, id=comment_id)
        form = CommentForm(request.POST or None, instance=comment)
        context = {'comment': comment,
                   'form': form}
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id)
        return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария к публикации"""
    author = get_author(Comment, post_id=post_id, id=comment_id)
    if author != request.user:
        return redirect('blog:post_detail', post_id)
    else:
        comment = get_object_or_404(Comment, post_id=post_id, id=comment_id)
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
    if profile != request.user:
        page_obj = get_paginator(request,
                                 is_published=True,
                                 category__is_published=True,
                                 pub_date__lte=datetime.now(),
                                 author=profile)
    else:
        page_obj = get_paginator(request,
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
