from .models import CustomUser
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
from .models import CustomUser, Materia, DisciplinaPessoa

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

def adicionar_aluno(request):
    if request.method == 'POST':
        pass
    return render(request, 'avaliacoes/adicionar_aluno.html')

def adicionar_disciplina(request):
    if request.method == 'POST':
        pass
    return render(request, 'avaliacoes/adicionar_disciplina.html')

def adicionar_professor(request):
    if request.method == 'POST':
        pass
    return render(request, 'avaliacoes/adicionar_professor.html')

def adicionar_usuario(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo_usuario')
        nome = request.POST.get('nome')
        imagem_perfil = request.FILES.get('imagem_perfil')
        if tipo == 'aluno':
            mensagem = f"Usuário {nome} (Aluno) cadastrado!"
        return HttpResponse(f"Cadastro concluído. {mensagem}")
        
    return render(request, 'avaliacoes/adicionar_usuario.html')
 
def lista_professores(request):
    # NOTA: Substitua 'Professor.objects.all()' pela sua lógica de filtro, se houver.
    # Se você estiver usando um modelo 'Usuario' com um campo 'tipo', filtre por ele:
    # professores = Usuario.objects.filter(tipo='professor')
    
    # Exemplo: Se usar um modelo Professor dedicado:
    # professores = Professor.objects.all().order_by('nome') 
    
    # Criando dados de exemplo, caso seus modelos ainda não estejam prontos:
    professores_exemplo = [
        {'id': 1, 'nome': 'Dr. João Silva', 'email': 'joao.silva@uni.edu', 'disciplinas': 'Cálculo, Álgebra Linear'},
        {'id': 2, 'nome': 'Dra. Maria Oliveira', 'email': 'maria.o@uni.edu', 'disciplinas': 'Física 1, Mecânica'},
        {'id': 3, 'nome': 'Prof. Pedro Costa', 'email': 'pedro.costa@uni.edu', 'disciplinas': 'Programação Web, Estrutura de Dados'},
    ]
    
    context = {
        'professores': professores_exemplo # Use 'professores' do DB quando estiver pronto
    }
    
    # NOTA: O template é 'avaliacoes/lista_professores.html'
    return render(request, 'avaliacoes/lista_professores.html', context)

def detalhes_professor(request, professor_id):
    
    # 1. Busca o professor pelo ID (retorna 404 se não encontrar)
    # Assumindo que o ID é o campo 'pk' do modelo Usuario
    professor = get_object_or_404(CustomUser, pk=professor_id, user_type='professor')
    
    # 2. Busca as avaliações/comentários relacionados ao professor (dados da parte inferior)
    # comentarios = Avaliacao.objects.filter(professor=professor).order_by('-data')
    
    # 3. Cria dados fictícios para o gráfico e comentários (Se você ainda não tem os modelos)
    
    # Dados para o gráfico Box Plot (Aqui você faria a média das avaliações)
    dados_grafico = {
        'didatica': [2, 4, 6, 8, 10],
        'dificuldade': [1, 3, 5, 7, 9],
        'relacionamento': [5, 6, 8, 9, 10],
        'pontualidade': [4, 7, 8, 9, 10],
    }

    comentarios_exemplo = [
        {'data': '12/09/2020 - 10:05:34', 'texto': 'Quando explica é ótima, mas perde muito o foco da aula, muito desorganizada, grossa como já mencionei, provas não condizentes com a lista, porém sempre generosa nas correções e tenta fazer com que vc passe na matéria.'},
        {'data': '20/06/2018 - 09:14:17', 'texto': 'expõe os alunos, é grossa desnecessariamente, porém, tem boa didática'},
        {'data': '14/12/2017 - 17:51:53', 'texto': 'Provas muito difíceis, e não condizentes com as listas.'},
    ]

    context = {
        'professor': professor,
        'dados_grafico': dados_grafico,
        'comentarios': comentarios_exemplo, # Substitua por 'comentarios' do DB
        # Dados Fictícios do Professor (Se o seu modelo Usuario não tiver todos esses campos)
        'departamento': 'Ciência da Computação', 
        'sala': '153A',
        'telefone': '(11) 3091-8898',
        'area': 'Álgebra Booleana'
    }

    return render(request, 'avaliacoes/detalhes_professor.html', context)