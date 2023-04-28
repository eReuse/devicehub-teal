import logging

import flask
from flask import Blueprint, request, url_for
from flask.views import View
from flask_login import current_user, login_required
from requests.exceptions import ConnectionError

from ereuse_devicehub import __version__, messages
from ereuse_devicehub.labels.forms import PrintLabelsForm, TagForm, TagUnnamedForm
from ereuse_devicehub.resources.lot.models import Lot, ShareLot
from ereuse_devicehub.resources.tag.model import Tag

labels = Blueprint('labels', __name__, url_prefix='/labels')

logger = logging.getLogger(__name__)


class TagListView(View):
    methods = ['GET']
    decorators = [login_required]
    template_name = 'labels/label_list.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        share_lots = ShareLot.query.filter_by(user_to_id=current_user.id)
        tags = Tag.query.filter(Tag.owner_id == current_user.id).order_by(
            Tag.created.desc()
        )
        context = {
            'lots': lots,
            'tags': tags,
            'page_title': 'Unique Identifiers Management',
            'version': __version__,
            'share_lots': share_lots,
        }
        return flask.render_template(self.template_name, **context)


class TagAddView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'labels/tag_create.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        share_lots = ShareLot.query.filter_by(user_to_id=current_user.id)
        context = {
            'page_title': 'New Tag',
            'lots': lots,
            'version': __version__,
            'share_lots': share_lots,
        }
        form = TagForm()
        if form.validate_on_submit():
            form.save()
            next_url = url_for('labels.label_list')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class TagAddUnnamedView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]
    template_name = 'labels/tag_create_unnamed.html'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        share_lots = ShareLot.query.filter_by(user_to_id=current_user.id)
        context = {
            'page_title': 'New Unnamed Tag',
            'lots': lots,
            'version': __version__,
            'share_lots': share_lots,
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

            next_url = url_for('labels.label_list')
            return flask.redirect(next_url)

        return flask.render_template(self.template_name, form=form, **context)


class PrintLabelsView(View):
    """This View is used to print labels from multiple devices"""

    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'labels/print_labels.html'
    title = 'Design and implementation of labels'

    def dispatch_request(self):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        share_lots = ShareLot.query.filter_by(user_to_id=current_user.id)
        context = {
            'lots': lots,
            'page_title': self.title,
            'version': __version__,
            'referrer': request.referrer,
            'share_lots': share_lots,
        }

        form = PrintLabelsForm()
        if form.validate_on_submit():
            context['form'] = form
            context['devices'] = form._devices
            return flask.render_template(self.template_name, **context)
        else:
            messages.error('Error you need select one or more devices')

        next_url = request.referrer or url_for('inventory.devicelist')
        return flask.redirect(next_url)


class LabelDetailView(View):
    """This View is used to print labels from multiple devices"""

    methods = ['POST', 'GET']
    decorators = [login_required]
    template_name = 'labels/print_labels.html'
    title = 'Design and implementation of labels'

    def dispatch_request(self, id):
        lots = Lot.query.filter(Lot.owner_id == current_user.id)
        share_lots = ShareLot.query.filter_by(user_to_id=current_user.id)
        tag = (
            Tag.query.filter(Tag.owner_id == current_user.id).filter(Tag.id == id).one()
        )
        context = {
            'lots': lots,
            'page_title': self.title,
            'version': __version__,
            'referrer': request.referrer,
            'share_lots': share_lots,
        }

        devices = []
        if tag.device:
            form = PrintLabelsForm(devices=str(tag.device.id))
            devices = [tag.device]
        else:
            form = PrintLabelsForm()

        form._devices = devices
        context['form'] = form
        context['devices'] = devices
        return flask.render_template(self.template_name, **context)


labels.add_url_rule('/', view_func=TagListView.as_view('label_list'))
labels.add_url_rule('/add/', view_func=TagAddView.as_view('tag_add'))
labels.add_url_rule(
    '/unnamed/add/', view_func=TagAddUnnamedView.as_view('tag_unnamed_add')
)
labels.add_url_rule(
    '/print',
    view_func=PrintLabelsView.as_view('print_labels'),
)
labels.add_url_rule('/<string:id>/', view_func=LabelDetailView.as_view('label_details'))
