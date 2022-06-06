from web.controllers.articles import get_rating
from . import ModuleError
from web.controllers import articles
from django.utils import html


def render(context, _params):
    if not context.article:
        raise ModuleError('Страница не указана')
    rating = get_rating(context.article)
    code = '<div class="w-rate-module page-rate-widget-box" data-page-id="%s">' % html.escape(context.article.full_name)
    code += '<span class="rate-points">рейтинг:&nbsp;<span class="number prw54353">%+d</span></span>' % rating
    code += '<span class="rateup btn btn-default"><a title="Мне нравится" href="#">+</a></span>'
    code += '<span class="ratedown btn btn-default"><a title="Мне не нравится" href="#">–</a></span>'
    code += '<span class="cancel btn btn-default"><a title="Отменить голос" href="#">x</a></span>'
    code += '</div>'
    return code


def allow_api():
    return True


def api_get_rating(context, _params):
    if not context.article:
        raise ModuleError('Страница не указана')
    return {'pageId': context.article.full_name, 'rating': articles.get_rating(context.article)}


def api_rate(context, params):
    if not context.article:
        raise ModuleError('Страница не указана')

    if not context.user.has_perm("web.can_vote_article"):
        raise ModuleError('Недостаточно прав')

    if 'value' not in params:
        raise ModuleError('Не указано значение оценки')

    articles.add_vote(context.article, context.user, params['value'])

    return api_get_rating(context, params)
