import logging

import flask
from flask import Blueprint, request, url_for
from flask.views import View
from flask_login import current_user, login_required
from requests.exceptions import ConnectionError

from ereuse_devicehub import __version__, messages
from ereuse_devicehub.label.forms import PrintLabelsForm, TagForm, TagUnnamedForm
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.tag.model import Tag

label = Blueprint('label', __name__, url_prefix='/label')

logger = logging.getLogger(__name__)


class TagListView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'label/label_list.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        tags = Tag.query.filter(Tag.owner_id == current_user.id).order_by(Tag.id)
        context = {
            'lots': lots,
            'tags': tags,
            'page_title': 'Tags Management',
            'version': __version__,
        }
        return flask.render_template(self.template_name, **context)


class TagAddView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'label/tag_create.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        context = {'page_title': 'New Tag', 'lots': lots, 'version': __version__}
        form = TagForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('label.label_list')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class TagAddUnnamedView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'label/tag_create_unnamed.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        context = {
            'page_title': 'New Unnamed Tag',
            'lots': lots,
            'version': __version__,
        }
        form = TagUnnamedForm()
        if form.validate_on_submit():
            try:
                form.save()
            except ConnectionError as e:
                logger.error(
                    "Error while trying to connect to tag server: {}".format(e)
                )
                msg = (
                    "Sorry, we cannot create the unnamed tags requested because "
                    "some error happens while connecting to the tag server!"
                )
                messages.error(msg)

            next_url = url_for('label.label_list')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class PrintLabelsView(View):
    """This View is used to print labels from multiple devices"""

    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'label/print_labels.html'
    title = 'Design and implementation of labels'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        context = {
            'lots': lots,
            'page_title': self.title,
            'version': __version__,
            'referrer': request.referrer,
        }

        form = PrintLabelsForm()
        if form.validate_on_submit():
            context['form'] = form
            context['tags'] = form._tags
            return flask.render_template(self.template_name, **context)
        else:
            messages.error('Error you need select one or more devices')

        next_url = request.referrer or url_for('inventory.devicelist')
        return flask.redirect(next_url)


class LabelDetailView(View):
    decorators = [login_required]
    template_name = 'label/label_detail.html'

    def dispatch_request(self, id):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        tag = (
            Tag.query.filter(Tag.owner_id == current_user.id).filter(Tag.id == id).one()
        )

        context = {
            'lots': lots,
            'tag': tag,
            'page_title': '{} Tag'.format(tag.code),
            'version': __version__,
        }
        return flask.render_template(self.template_name, **context)


label.add_url_rule('/', view_func=TagListView.as_view('label_list'))
label.add_url_rule('/add/', view_func=TagAddView.as_view('tag_add'))
label.add_url_rule(
    '/unnamed/add/', view_func=TagAddUnnamedView.as_view('tag_unnamed_add')
)
label.add_url_rule(
    '/print',
    view_func=PrintLabelsView.as_view('print_labels'),
)
label.add_url_rule('/<string:id>/', view_func=LabelDetailView.as_view('label_details'))
