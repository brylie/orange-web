import random
import re
import requests
import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render
from django.core.mail import send_mail

from homepage.templatetags.tag_extras import download_choices

from orange_web.resources import FEATURE_DESCRIPTIONS
from orange_web.resources import SCREENSHOTS
from orange_web.resources import WIDGET_JS
from orange_web.resources import WIDG_JS
from orange_web.resources import LICENSE
from orange_web.resources import ADMINS
from orange_web.resources import TESTIMONIALS


def screens(request):
    """Sort screenshots by their rank"""
    SCREENSHOTS.sort(key=lambda a: a['rank'])
    return render(request, 'screenshots.html', {'screenshots': SCREENSHOTS})


def toolbox(request):
    return render(request, 'toolbox.html', {
        'toolbox': WIDGET_JS,
        'toolbox_strings': json.dumps(WIDG_JS),
    })


def license_page(request):
    text = ''
    in_other = False
    other = []
    for l in LICENSE:
        if l.startswith('----'):
            in_other = not in_other
            if in_other:
                other.append(l)
            else:
                other[-1] += l.rstrip()
        elif in_other:
            other[-1] += l
        else:
            text += l
    context = {
        'text': text,
        'other': other,
    }
    return render(request, 'license.html', context)


def pass_captcha(request):
    url = 'https://www.google.com/recaptcha/api/siteverify'
    params = {
        'secret': settings.RECAPTCHA_SECRET,
        'response': request.POST.get('g-recaptcha-response')
    }
    r = requests.get(url, params=params)
    return json.loads(r.content).get('success')


def contribute(request):
    response = {'post': 0}
    if request.method == 'POST':
        rp = request.POST
        if not pass_captcha(request):
            response['post'] = -2
        elif rp.get('Signature') != 'I AGREE':
            response['post'] = -1
        else:
            message = ('This message was sent to you automatically from '
                       'orange.biolab.si.\n\n{0} electronically signed '
                       'Orange Contributor License Agreement. Below are '
                       'his/her contact information:\n\nFull Name: {0}\n'
                       'E-mail: {1}\nMailing Address: \n\n{2}\n\nCountry: {3}'
                       '\nTelephone Number: {4}\n\nThe user has confirmed '
                       'this action by typing "I AGREE" in the appropriate '
                       'Electronic Signature form field.\n\nGood day,\n'
                       'Biolab Webmaster').format(rp.get('Full Name'),
                                                  rp.get('E-mail'),
                                                  rp.get('Address'),
                                                  rp.get('Country'),
                                                  rp.get('Number'))
            send_mail('Orange Contributor License Agreement Receipt', message,
                      rp.get('E-mail'), ADMINS, fail_silently=True)
            response['post'] = 1
    return render(request, 'contributing-to-orange.html', response)


def contact(request):
    response = {'post': 0}
    if request.method == 'POST':
        rp = request.POST
        if pass_captcha(request):
            message = (u'This message was sent to you automatically from '
                       'orange.biolab.si.\n\nA visitor submitted the contact '
                       'form. Below are the details:\n\nE-mail: {0}\nSubject: '
                       '{1}\nMessage:\n\n{2}\n\nGood day,\n'
                       'Biolab Webmaster').format(rp.get('E-mail'),
                                                  rp.get('Subject'),
                                                  rp.get('Message'))
            send_mail('Orange Contact Request', message,
                      rp.get('E-mail'), ADMINS, fail_silently=True)
            response['post'] = 1
        else:
            response['post'] = -1
    return render(request, 'contact.html', response)

# Regex objects for browser OS detection
p_win = re.compile(r'.*[Ww]in.*')
p_mac = re.compile(r'^(?!.*(iPhone|iPad)).*[Mm]ac.*')
p_linux = re.compile(r'.*[Ll]inux.*')


def detect_os(user_agent):
    if re.match(p_win, user_agent):
        return 'windows'
    elif re.match(p_mac, user_agent):
        return 'mac-os-x'
    elif re.match(p_linux, user_agent):
        return 'linux'
    else:
        return ''


def index(request):
    response = {
        'random_screenshots': random.sample(SCREENSHOTS, 5),
        'os': detect_os(request.META.get('HTTP_USER_AGENT', '')),
        'features': FEATURE_DESCRIPTIONS,
        'testimonials': TESTIMONIALS[:3],
    }
    return render(request, 'homepage.html', response)


def download(request, os=None):
    if os is None:
        os = detect_os(request.META.get('HTTP_USER_AGENT', ''))

    return render(request, 'download.html', dict(
        os=os,
        tabs=[
            dict(icon="windows", title="Windows", os="windows"),
            dict(icon="apple", title="macOS", os="mac-os-x"),
            dict(icon="linux", title="Linux / Source", os="linux"),
        ],
        recommended=recommended_download(os)
    ))


VERSION_RE = re.compile(r"Orange3-([\d\.]+)\.")


def recommended_download(os):
    downloads = download_choices()

    def get_version(filename):
        try:
            return VERSION_RE.findall(filename)[0]
        except IndexError:
            return "unknown"

    filename = title = ""
    if os == "windows":
        title = "Windows Installer"
        filename = downloads["orange3-win32-installer"]
    elif os == "mac-os-x":
        title = "macOS bundle"
        filename = downloads["bundle-orange3"]

    if filename:
        return dict(
            filename=filename,
            url=reverse('download') + 'files/' + filename,
            version=get_version(filename),
            title=title
        )
    else:
        return None


def start(request):
    return render(request, 'start.html',
                  {'screens_root': 'homepage/getting_started'})


def privacy(request):
    return render(request, 'privacy_policy.html', {})


def latest_version(request):
    version = download_choices('mac').get('version', '')
    return HttpResponse(version, content_type="text/plain")
