from django.shortcuts import render, redirect, get_object_or_404
from .forms import AvaliacaoForm, MateriaForm, ProfessorForm, UserForm
from .models import Avaliacao, Professor
from django.db.models import Avg
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.contrib import messages


@login_required(login_url='login')
def home(request):
    return render(request, 'avaliacoes/home.html')

def index(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        return redirect('login')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        next_url = request.POST.get('next') or request.GET.get('next') or 'home'
        if user is not None:
            login(request, user)
            return redirect(next_url)
        else:
            error = 'Usuário ou senha inválidos'
            return render(request, 'avaliacoes/login.html', {'error': error})
    else:
        return render(request, 'avaliacoes/login.html')

@login_required(login_url='login')
def home(request):
    return render(request, 'avaliacoes/home.html')

@login_required(login_url='login')
def lista_professores(request):
    professores = Professor.objects.annotate(
        media_nota=Avg('user__disciplinas_pessoa__avaliacoes__categorias_avaliacao__nota')
    ).filter(id__isnull=False)

    return render(request, 'avaliacoes/lista_professores.html', {'professores': professores})

@login_required(login_url='login')
def enviar_avaliacao(request):
    professor_id = request.GET.get('professor_id')
    professor = None
    if professor_id:
        try:
            professor = Professor.objects.get(pk=professor_id)
        except Professor.DoesNotExist:
            professor = None

    if request.method == 'POST':
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('obrigado')
    else:
        initial_data = {'professor': professor} if professor else {}
        form = AvaliacaoForm(initial=initial_data)

    return render(request, 'avaliacoes/enviar_avaliacao.html', {'form': form})

@login_required(login_url='login')
def obrigado(request):
    return render(request, 'avaliacoes/obrigado.html')

@login_required(login_url='login')
def dashboard_grafico(request):
    professores = Professor.objects.annotate(
        media_nota=Avg('user__disciplinas_pessoa__avaliacoes__categorias_avaliacao__nota')
    )

    nomes = [prof.user.get_full_name() or prof.user.username for prof in professores]
    medias = [prof.media_nota or 0 for prof in professores]

    context = {
        'nomes_json': json.dumps(nomes),
        'medias_json': json.dumps(medias),
    }
    return render(request, 'avaliacoes/dashboard_grafico.html', context)

@login_required(login_url='login')
def lista_comentarios(request):
    comentarios = Avaliacao.objects.filter(
        comentario__isnull=False
    ).exclude(
        comentario=''
    ).select_related(
        'disciplina_pessoa__pessoa'
    )
    return render(request, 'avaliacoes/lista_comentarios.html', {'comentarios': comentarios})

@login_required(login_url='login')
def detalhes_professor(request, professor_id):
    professor = get_object_or_404(Professor, pk=professor_id)
    avaliacoes = Avaliacao.objects.filter(
        disciplina_pessoa__pessoa=professor.user
    ).prefetch_related('categorias_avaliacao')
    
    # Média das notas nas categorias das avaliações do professor:
    media_nota = avaliacoes.aggregate(
        media=Avg('categorias_avaliacao__nota')
    )['media'] or 0

    return render(request, 'avaliacoes/detalhes_professor.html', {
        'professor': professor,
        'avaliacoes': avaliacoes,
        'media_nota': media_nota,
    })

@staff_member_required
def admin_cadastro(request):
    if request.method == 'POST':
        if 'submit_materia' in request.POST:
            materia_form = MateriaForm(request.POST, prefix='materia')
            professor_form = ProfessorForm(prefix='professor')
            user_form = UserForm(prefix='user')
            if materia_form.is_valid():
                materia_form.save()
                messages.success(request, 'Matéria cadastrada com sucesso!')
                return redirect('admin_cadastro')

        elif 'submit_professor' in request.POST:
            materia_form = MateriaForm(prefix='materia')
            professor_form = ProfessorForm(request.POST, request.FILES, prefix='professor')
            user_form = UserForm(prefix='user')
            if professor_form.is_valid():
                professor_form.save()
                messages.success(request, 'Professor cadastrado com sucesso!')
                return redirect('admin_cadastro')

        elif 'submit_usuario' in request.POST:
            materia_form = MateriaForm(prefix='materia')
            professor_form = ProfessorForm(prefix='professor')
            user_form = UserForm(request.POST, prefix='user')
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Usuário cadastrado com sucesso!')
                return redirect('admin_cadastro')

    else:
        materia_form = MateriaForm(prefix='materia')
        professor_form = ProfessorForm(prefix='professor')
        user_form = UserForm(prefix='user')

    context = {
        'materia_form': materia_form,
        'professor_form': professor_form,
        'user_form': user_form,
    }
    return render(request, 'avaliacoes/admin_cadastro.html', context)

 