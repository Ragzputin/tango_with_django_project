from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.forms import UserForm, UserProfileForm
from datetime import datetime
from rango.bing_search import run_query


def index(request):

    context = RequestContext(request)

    cat_list = get_category_list()

    top_five_cats = Category.objects.order_by('-views')[:5]

    EncodeUrl(top_five_cats)

    top_pgs = Page.objects.order_by('-views')[:5]

    context_dict = {'cat_list': cat_list, 'top_five_cats': top_five_cats, 'top_pgs': top_pgs}

    Session(request)

    # Render and return the rendered response back to the user.
    return render_to_response('rango/index.html',context_dict,context)

def get_category_list(max_results=0, starts_with=''):
    cat_list = []
    if starts_with:
        cat_list = Category.objects.filter(name__istartswith=starts_with)
    else:
        cat_list = Category.objects.all()

    if max_results > 0:
        if len(cat_list) > max_results:
            cat_list = cat_list[:max_results]

    EncodeUrl(cat_list)

    return cat_list

def suggest_category(request):
    context = RequestContext(request)
    cat_list = []
    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']

    cat_list = get_category_list(8, starts_with)

    return render_to_response('rango/category_list.html', {'cat_list': cat_list}, context)

@login_required
def auto_add_page(request):
    context = RequestContext(request)
    cat_id = None
    url = None
    context_dict = {}

    if request.method == 'GET':
        cat_id = request.GET['category_id']
        url = request.GET['url']
        title = request.GET['title']

        print
        print "cat_id: ", cat_id
        print
        print "url: ", url
        print
        print "title: ", title
        if cat_id:
            category = Category.objects.get(id=int(cat_id))
            context_dict['category_name'] = category.name
            pg = Page.objects.get_or_create(category=category, title=title, url=url)

            pages = Page.objects.filter(category=category).order_by('-views')

            # Adds our results list to the template context under name pages.
            context_dict['pages'] = pages

    return render_to_response('rango/page_list.html', context_dict, context)

def about(request):
    context = RequestContext(request)

    cat_list = get_category_list()

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

    return render_to_response('rango/about.html', {'visits': count, 'cat_list': cat_list}, context)

def category(request, category_name_url):
    context = RequestContext(request)

    cat_list = get_category_list()

    category_name = DecodeUrl(category_name_url)

    context_dict = {'category_name': category_name, 'category_name_url': category_name_url}

    try:
        category = Category.objects.get(name=category_name)
        category.views += 1
        category.save()

        pages = Page.objects.filter(category=category)

        context_dict['pages'] = pages

        context_dict['category'] = category

        context_dict['cat_list'] = cat_list

    except Category.DoesNotExist:
        pass

    result_list = []
    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)
            context_dict['result_list'] = result_list

    return render_to_response('rango/category.html', context_dict, context)

@login_required
def like_category(request):
    context = RequestContext(request)
    cat_id = None
    if request.method == 'GET':
        if 'category_id' in request.GET:
            cat_id = request.GET['category_id']
            likes = 0
            category = Category.objects.get(id=int(cat_id))
            if category:
                print "entered category"
                likes = category.likes + 1
                category.likes = likes
                category.save()

    return HttpResponse(likes)

def add_category(request):
    context = RequestContext(request)

    cat_list = get_category_list()

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
    return render_to_response('rango/add_category.html', {'form': form, 'cat_list': cat_list}, context)

def add_page(request, category_name_url):
    context = RequestContext(request)

    cat_list = get_category_list()

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
        category_name, 'form': form, 'cat_list': cat_list}, context)

def track_url(request):
    context = RequestContext(request)
    page_id = None
    url = '/rango/'

    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

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

"""
def search(request):
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'result_list': result_list}, context)
"""

@login_required
def profile(request):
    context = RequestContext(request)
    cat_list = Category.objects.all()
    context_dict = {'cat_list': cat_list}
    u = User.objects.get(username=request.user)

    try:
        up = UserProfile.objects.get(user=u)
    except:
        up = None

    context_dict['user'] = u
    context_dict['userprofile'] = up
    return render_to_response('rango/profile.html', context_dict, context)

@login_required
def restricted(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    context_dict = {'restricted':'Since you\'re logged in, you can see this text!', 'cat_list': cat_list}
    return render_to_response('rango/restricted.html',context_dict,context)

@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/rango/')

def EncodeUrl(cats):
    for category in cats:
        category.url = category.name.replace(' ','_')

def DecodeUrl(cat_url):
    cat_name = cat_url.replace('_', ' ')
    return cat_name

def Session(request):
    if request.session.get('last_visit'):
        # The session has a value for the last visit
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).seconds > 5:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        # The get returns None, and the session does not have a value for the last visit.
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

