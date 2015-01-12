from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response
from rango.models import Category, Page
from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.forms import UserForm, UserProfileForm
from datetime import datetime

cat_url_list = []
enc_bool = False

def index(request):
    context = RequestContext(request)

    category_list = Category.objects.all()

    top_five_cats = Category.objects.order_by('-views')[:5]

    if enc_bool == False:
        EncodeUrl(category_list, top_five_cats)

    context_dict = {'categories': category_list, 'top_five_cats': top_five_cats}

    if request.session.get('last_visit'):
        # The session has a value for the last visit
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        # The get returns None, and the session does not have a value for the last visit.
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

    # Render and return the rendered response back to the user.
    return render_to_response('rango/index.html',context_dict,context)

def about(request):
    context = RequestContext(request)

    if request.session.get('last_visit'):
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).seconds > 5:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = str(datetime.now())

    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0

    return render_to_response('rango/about.html', {'visits': count}, context)

def category(request, category_name_url):
    context = RequestContext(request)

    category_name = DecodeUrl(category_name_url)

    context_dict = {'category_name': category_name, 'category_name_url': category_name_url}

    try:
        category = Category.objects.get(name=category_name)

        pages = Page.objects.filter(category=category)

        context_dict['pages'] = pages

        context_dict['category'] = category

    except Category.DoesNotExist:
        pass


    return render_to_response('rango/category.html', context_dict, context)

def add_category(request):
    context = RequestContext(request)

    #HTTP POST
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        #Have we been provided with a valid form
        if form.is_valid():
            #save new category to database
            form.save(commit=True)

            #return to index view.
            #User will now see the homepage
            return index(request)
        else:
            #the supplied form contains errors - print these to terminal
            print form.errors
    else:
        #if the request was not a POST, display the form to enter details
        form = CategoryForm()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render_to_response('rango/add_category.html', {'form': form}, context)

def add_page(request, category_name_url):
    context = RequestContext(request)

    category_name = DecodeUrl(category_name_url)
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            page = form.save(commit=False)

            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html',{},context)

            # Also, create a default value for the number of views.
            page.views = 0

            # With this, we can then save our new model instance.
            page.save()

            # Now that the page is saved, display the category instead.
            return category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()

    return render_to_response('rango/add_page.html', {'category_name_url': category_name_url,'category_name': \
        category_name, 'form': form}, context)

def register(request):
    context = RequestContext(request)

    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()

            registered = True

        else:
            print user_form.errors, profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render_to_response(
        'rango/register.html', {'user_form': user_form, 'profile_form': profile_form, 'registered': registered},
        context
    )

def user_login(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username,password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print "Invalid login details: {0}, {1}".format(username,password)
            return HttpResponse("Invalid username or password entered.")

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render_to_response('rango/login.html',{},context)

@login_required
def restricted(request):
    context = RequestContext(request)
    context_dict = {'restricted':'Since you\'re logged in, you can see this text!'}
    return render_to_response('rango/restricted.html',context_dict,context)

@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/rango/')

def EncodeUrl(category_list, top_five_cats):
    enc_bool = True
    for category in category_list:
        category.url = category.name.replace(' ','_')
        cat_url_list.append(category.url)

    for category in top_five_cats:
        category.url = category.name.replace(' ','_')


def DecodeUrl(cat_url):
    #cat_name = ''
    for url in cat_url_list:
        if cat_url == url:
            cat_name = url.replace('_', ' ')
            break

    return cat_name


