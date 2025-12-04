# avaliacoes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .forms import (
    AvaliacaoForm, MateriaForm, ProfessorForm, UserForm,
    # Imports adicionados:
    UserProfileForm, DisciplinaPessoaForm 
)
from .models import (
    Avaliacao, Professor, CustomUser, Materia, DisciplinaPessoa, 
    Aluno, Categoria, AvaliacaoCategoria,MatriculaAluno
)
from django.db.models import Avg, Count, Q
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.contrib import messages
from datetime import datetime
from django.db.models import Value, CharField
from django.db.models.functions import Concat
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import IntegrityError # Import adicionado
from .models import MensagemContato # Importe o modelo novo
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.db import transaction

from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from django.views.decorators.csrf import csrf_exempt

from unidecode import unidecode

@login_required(login_url='login')


def home(request):
    # 1. Calcular a média geral da faculdade (de 0 a 10)
    media_geral_dict = AvaliacaoCategoria.objects.aggregate(media=Avg('nota'))
    media_geral = media_geral_dict.get('media') or 0.0

    # 2. Calcular o total de avaliações
    total_avaliacoes = Avaliacao.objects.count()
    
    # 3. NOVO: Calcular a porcentagem para o gráfico
    # (media_geral / 10) * 100 = media_geral * 10
    media_percent = (media_geral / 10) * 100 if media_geral > 0 else 0

    context = {
        'media_geral_faculdade': round(media_geral, 1),
        'media_percent_faculdade': media_percent, # <-- Variável para o gráfico
        'total_avaliacoes': total_avaliacoes,
        # (Não precisamos mais do 'nome_aluno', usamos request.user.first_name no template)
    }
    return render(request, 'avaliacoes/home.html', context)
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
def lista_professores(request):
    # Inicia a query base
    professores = Professor.objects.annotate(
        media_nota=Avg('user__disciplinas_pessoa__avaliacoes__categorias_avaliacao__nota')
    ).filter(id__isnull=False).order_by('user__first_name')

    # --- LÓGICA DE PESQUISA ---
    query_professor = request.GET.get('q_professor', '').strip()
    query_disciplina = request.GET.get('q_disciplina', '').strip()

    if query_professor:
        # AQUI ESTA A CORREÇÃO:
        # Criamos um campo virtual 'nome_completo' juntando First + Espaço + Last
        professores = professores.annotate(
            nome_completo=Concat(
                'user__first_name', 
                Value(' '), 
                'user__last_name', 
                output_field=CharField()
            )
        ).filter(
            # Agora pesquisamos no nome, no sobrenome OU na junção dos dois
            Q(user__first_name__icontains=query_professor) | 
            Q(user__last_name__icontains=query_professor) |
            Q(nome_completo__icontains=query_professor)
        )

    if query_disciplina:
        professores = professores.filter(
            user__disciplinas_pessoa__disciplina__nome__icontains=query_disciplina
        ).distinct()

    context = {
        'professores': professores,
        'query_professor': query_professor,
        'query_disciplina': query_disciplina
    }
    return render(request, 'avaliacoes/lista_professores.html', context)

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
        # 1. Captura os dados (APENAS NOME E DATA)
        nome = request.POST.get('nome')
        data_inicio_str = request.POST.get('data_inicio')

        # 2. Validação de campos preenchidos
        if not nome or not data_inicio_str:
            messages.error(request, "Os campos 'Nome' e 'Data de Início' são obrigatórios.")
            return render(request, 'avaliacoes/adicionar_disciplina.html')

        # 2a. NOVO: Valida se o NOME já existe (case-insensitive)
        if Materia.objects.filter(nome__iexact=nome).exists():
            messages.error(request, f"Já existe uma disciplina cadastrada com o nome '{nome}'.")
            return render(request, 'avaliacoes/adicionar_disciplina.html')
        
        # 2b. Valida a data
        data_inicio_obj = None
        try:
            data_inicio_obj = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()
        except ValueError:
            messages.error(request, "Data de Início inválida. O formato deve ser DD/MM/AAAA.")
            return render(request, 'avaliacoes/adicionar_disciplina.html')

        # 3. NOVO: Lógica de Geração Automática do Código
        try:
            # Pega as iniciais das palavras (ex: "Cálculo Diferencial" -> "CD")
            palavras = nome.split()
            ignore = ['e', 'de', 'da', 'do', 'das', 'dos', 'para']
            iniciais = ""
            for p in palavras:
                if p.lower() not in ignore and p.strip():
                    iniciais += p[0].upper()
            
            # Se for muito curto (ex: "Redes"), usa as 3 primeiras letras
            if len(iniciais) < 2 and len(nome) >= 3:
                iniciais = nome[0:3].upper()
            elif not iniciais:
                iniciais = "DISC" # Caso de fallback
            
            # Busca quantos códigos já existem com essas iniciais (ex: 'CD')
            count = Materia.objects.filter(codigo__startswith=iniciais).count()
            
            # Gera o código final (ex: 'CD001', 'CD002')
            # :03d significa "formate com 3 dígitos, preenchendo com zeros"
            novo_codigo = f"{iniciais}{count + 1:03d}"
            
            # Checagem final de segurança (raro, mas possível)
            while Materia.objects.filter(codigo=novo_codigo).exists():
                count += 1
                novo_codigo = f"{iniciais}{count + 1:03d}"

            # 4. Salva no banco com o código gerado
            Materia.objects.create(
                nome=nome,
                codigo=novo_codigo, # <- Usa o código gerado
                data_inicio=data_inicio_obj
            )
            
            # NOVO: Mostra o código gerado na mensagem de sucesso
            messages.success(request, f"Disciplina '{nome}' (Cód: {novo_codigo}) adicionada com sucesso!")
            return redirect('adicionar_disciplina') 

        except Exception as e:
            messages.error(request, f"Erro inesperado ao gerar código ou salvar: {e}")
            return render(request, 'avaliacoes/adicionar_disciplina.html')

    # Se for um request GET, apenas renderiza a página
    return render(request, 'avaliacoes/adicionar_disciplina.html')
# ... (restante das views, como adicionar_disciplina, adicionar_professor, etc.)

# SEU ARQUIVO: avaliacoes/views.py

# No topo do seu views.py, garanta que get_object_or_404 está importado:
from django.shortcuts import render, redirect, get_object_or_404
# ...e que todos os seus models estão importados:
from .models import CustomUser, Materia, DisciplinaPessoa, Professor, Aluno
# ...outros imports...

@staff_member_required 
def adicionar_usuario(request):
    if request.method == 'POST':
        # --- 1. CAPTURA DOS DADOS ---
        tipo = request.POST.get('tipo_usuario')
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        cpf = request.POST.get('cpf')
        data_nascimento_str = request.POST.get('nascimento')
        imagem_perfil = request.FILES.get('imagem_perfil')
        materia_id = request.POST.get('materia_disciplina')

        # --- 2. VALIDAÇÕES ---
        if not all([tipo, nome, email, cpf, data_nascimento_str]):
             messages.error(request, "Preencha todos os campos obrigatórios.")
             return redirect('adicionar_usuario')

        materia_obj = None
        if tipo == 'professor':
            if not materia_id:
                messages.error(request, "Selecione uma disciplina para o professor.")
                return redirect('adicionar_usuario')
            try:
                materia_obj = Materia.objects.get(pk=materia_id)
            except Materia.DoesNotExist:
                messages.error(request, "Disciplina inválida.")
                return redirect('adicionar_usuario')

        try:
            data_nascimento_obj = datetime.strptime(data_nascimento_str, '%d/%m/%Y').date()
        except ValueError:
            messages.error(request, "Data inválida (DD/MM/AAAA).")
            return redirect('adicionar_usuario')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email já cadastrado.")
            return redirect('adicionar_usuario')
        if CustomUser.objects.filter(cpf=cpf).exists():
            messages.error(request, "CPF já cadastrado.")
            return redirect('adicionar_usuario')

        # --- 3. CRIAÇÃO NO BANCO (RÁPIDA) ---
        novo_user = None
        try:
            # O atomic garante que Usuário e Perfil sejam criados juntos.
            # Se der erro aqui, nada é salvo.
            with transaction.atomic():
                
                nome_parts = nome.split(' ')
                first_name = nome_parts[0]
                last_name = ' '.join(nome_parts[1:]) if len(nome_parts) > 1 else ''

                # Gera senha e cria User
                senha_temp = get_random_string(12)
                novo_user = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    password=senha_temp,
                    user_type=tipo,
                    cpf=cpf,
                    data_nascimento=data_nascimento_obj,
                    is_active=True,
                    first_name=first_name,
                    last_name=last_name
                )

                # Cria Perfil
                if tipo == 'professor':
                    Professor.objects.create(user=novo_user, foto=imagem_perfil)
                    DisciplinaPessoa.objects.create(disciplina=materia_obj, pessoa=novo_user)
                elif tipo == 'aluno':
                    Aluno.objects.create(user=novo_user)
                elif tipo == 'administrador':
                    novo_user.is_staff = True
                    novo_user.is_superuser = True
                    novo_user.save()
            
            # --- FIM DO BLOCO ATOMIC ---
            # O banco de dados foi salvo e liberado AQUI.
            
        except Exception as e:
            # Erro de banco de dados
            messages.error(request, f"Erro ao salvar no banco: {e}")
            return redirect('adicionar_usuario')

        # --- 4. ENVIO DE EMAIL (LENTO) ---
        # Agora estamos fora da transação, então se demorar, não trava o banco.
        try:
            print(f"DEBUG: Enviando email para {email}")
            reset_form = PasswordResetForm({'email': email})
            if reset_form.is_valid():
                reset_form.save(
                    request=request,
                    use_https=request.is_secure(),
                    subject_template_name='avaliacoes/password_reset_subject.txt',
                    email_template_name='avaliacoes/password_reset_email.html',
                )
        except Exception as e_mail:
            # Se o email falhar, o usuário JÁ FOI CRIADO. 
            # Apenas avisamos o admin, não deletamos o usuário.
            messages.warning(request, f"Usuário criado, mas erro ao enviar email: {e_mail}")
            return redirect('adicionar_usuario')

        # Sucesso total
        if tipo == 'professor':
            messages.success(request, f"Professor {nome} cadastrado e e-mail enviado!")
            return redirect('lista_professores')
        else:
            messages.success(request, f"{tipo.capitalize()} {nome} cadastrado e e-mail enviado!")
            return redirect('adicionar_usuario')

    # --- GET Request ---
    materias = Materia.objects.all().order_by('nome')
    return render(request, 'avaliacoes/adicionar_usuario.html', {'materias': materias})




def detalhes_professor(request, professor_id):
    # 1. Busca o professor
    professor = get_object_or_404(Professor, pk=professor_id)
    
    # 2. Busca as "turmas" (DisciplinaPessoa) deste professor
    disciplinas_do_professor = DisciplinaPessoa.objects.filter(pessoa=professor.user).select_related('disciplina')

    # 3. Busca os comentários
    comentarios = Avaliacao.objects.filter(
        disciplina_pessoa__pessoa=professor.user,
        comentario__isnull=False
    ).exclude(comentario='').order_by('-data_avaliacao') 

    # =======================================================
    # NOVO: VERIFICAÇÃO DA CONDIÇÃO DE AVALIAÇÃO (pode_avaliar)
    # =======================================================
    pode_avaliar = False
    disciplinas_permitidas_ids = []
    disciplinas_avaliadas_ids = [] # <-- VARIÁVEL PARA GUARDAR OS IDS JÁ AVALIADOS
    
    # Verifica se o usuário está logado E se é do tipo 'aluno'
    if request.user.is_authenticated and request.user.user_type == 'aluno':
        try:
            # 3a. Busca o perfil Aluno do usuário logado
            aluno_logado = Aluno.objects.get(user=request.user)
            
            # 3b. OBTÉM IDS DOS VÍNCULOS QUE O ALUNO ESTÁ MATRICULADO (Permissão de Acesso)
            disciplinas_permitidas_ids = list(MatriculaAluno.objects.filter(
                aluno=aluno_logado,
                disciplina_professor__pessoa=professor.user
            ).values_list('disciplina_professor_id', flat=True)) # Pega o ID do DisciplinaPessoa

            if disciplinas_permitidas_ids:
                pode_avaliar = True
                
                # NOVO: OBTÉM IDS DOS VÍNCULOS QUE O ALUNO JÁ AVALIOU
                # Filtra as Avaliacoes por aluno e pelo conjunto de disciplinas permitidas
                disciplinas_avaliadas_ids = list(Avaliacao.objects.filter(
                    aluno=aluno_logado,
                    disciplina_pessoa__in=disciplinas_permitidas_ids
                ).values_list('disciplina_pessoa_id', flat=True).distinct()) # Pega o ID do DisciplinaPessoa avaliado
                
        except Aluno.DoesNotExist:
            pass
    # =======================================================
    # FIM DA VERIFICAÇÃO
    # =======================================================

    # 4. === Lógica do Gráfico por Disciplina ===
    
    # Dicionário principal que será enviado como JSON
    dados_grafico = {}
    
    # Listas para guardar a média GERAL (de todas as disciplinas)
    dados_all = {
        'didatica': [], 'dificuldade': [], 'relacionamento': [], 'pontualidade': []
    }

    # Busca as 4 categorias de uma vez para evitar buscas repetidas no loop
    try:
        cat_didatica = Categoria.objects.get(nome_categoria='Didática')
        cat_dificuldade = Categoria.objects.get(nome_categoria='Dificuldade')
        cat_relacionamento = Categoria.objects.get(nome_categoria='Relacionamento')
        cat_pontualidade = Categoria.objects.get(nome_categoria='Pontualidade')
    except Categoria.DoesNotExist as e:
        # Se as categorias não existirem, envia dados vazios
        context = {
            'professor': professor,
            'disciplinas_professor': disciplinas_do_professor,
            'comentarios': comentarios,
            'dados_grafico_json': json.dumps({'all': dados_all}),
            'pode_avaliar': pode_avaliar,
            'disciplinas_permitidas_json': json.dumps(disciplinas_permitidas_ids),
            'disciplinas_avaliadas_json': json.dumps(disciplinas_avaliadas_ids), # ENVIADO AQUI
        }
        return render(request, 'avaliacoes/detalhes_professor.html', context)


    # Loop por cada disciplina que o professor ministra
    for dp in disciplinas_do_professor:
        # Pega as notas APENAS dessa disciplina (dp)
        notas_disciplina = AvaliacaoCategoria.objects.filter(avaliacao__disciplina_pessoa=dp)
        
        # Filtra as notas por categoria
        notas_didatica = list(notas_disciplina.filter(categoria=cat_didatica).values_list('nota', flat=True))
        notas_dificuldade = list(notas_disciplina.filter(categoria=cat_dificuldade).values_list('nota', flat=True))
        notas_relacionamento = list(notas_disciplina.filter(categoria=cat_relacionamento).values_list('nota', flat=True))
        notas_pontualidade = list(notas_disciplina.filter(categoria=cat_pontualidade).values_list('nota', flat=True))
        
        # Adiciona os dados dessa disciplina ao dicionário principal, usando o ID como chave
        dados_grafico[dp.pk] = {
            'didatica': notas_didatica,
            'dificuldade': notas_dificuldade,
            'relacionamento': notas_relacionamento,
            'pontualidade': notas_pontualidade,
        }
        
        # Adiciona essas notas também à média GERAL (all)
        dados_all['didatica'].extend(notas_didatica)
        dados_all['dificuldade'].extend(notas_dificuldade)
        dados_all['relacionamento'].extend(notas_relacionamento)
        dados_all['pontualidade'].extend(notas_pontualidade)

    # Adiciona a média GERAL ao dicionário com a chave 'all'
    dados_grafico['all'] = dados_all
    
    context = {
        'professor': professor,
        'disciplinas_professor': disciplinas_do_professor, # Para o dropdown
        'comentarios': comentarios,
        'dados_grafico_json': json.dumps(dados_grafico, default=str), # Envia o NOVO JSON
        'pode_avaliar': pode_avaliar,
        'disciplinas_permitidas_json': json.dumps(disciplinas_permitidas_ids),
        'disciplinas_avaliadas_json': json.dumps(disciplinas_avaliadas_ids), # ENVIADO AQUI
    }

    return render(request, 'avaliacoes/detalhes_professor.html', context)

@require_POST
@login_required # Garante que o usuário está logado
@transaction.atomic # Garante que todas as operações de DB sejam bem-sucedidas
def salvar_avaliacao_api(request):
    try:
        data = json.loads(request.body)
        disciplina_pessoa_id = data.get('disciplina_pessoa_id')
        
        comentario_texto = data.get('comentario', '').strip()

        if not disciplina_pessoa_id:
            return JsonResponse({'success': False, 'error': 'Disciplina não selecionada'}, status=400)

        # 1. VALIDAÇÃO DE PERMISSÃO E MATRÍCULA
        
        # 1a. Verifica se o usuário logado é um Aluno
        if request.user.user_type != 'aluno':
            return JsonResponse({'success': False, 'error': 'Acesso negado. Apenas alunos podem enviar avaliações.'}, status=403)
        
        try:
            # Tenta buscar o perfil Aluno e o vínculo DisciplinaPessoa
            aluno_logado = Aluno.objects.get(user=request.user)
            disciplina_pessoa = get_object_or_404(DisciplinaPessoa, pk=disciplina_pessoa_id)
            
            # 1b. Verifica se o Aluno está ATUALMENTE matriculado
            if not MatriculaAluno.objects.filter(aluno=aluno_logado, disciplina_professor=disciplina_pessoa).exists():
                 return JsonResponse({'success': False, 'error': 'Você não está matriculado nesta disciplina e não pode avaliá-la.'}, status=403)
                 
            # 1c. NOVO BLOQUEIO: Verifica se a avaliação já existe
            # ESTA CHECAGEM SÓ FUNCIONA SE SUA MODEL 'Avaliacao' TIVER UM CAMPO ForeignKey PARA 'aluno'
            if Avaliacao.objects.filter(disciplina_pessoa=disciplina_pessoa, aluno=aluno_logado).exists():
                 return JsonResponse({'success': False, 'error': 'Você já enviou uma avaliação para esta disciplina.'}, status=403)
                 
        except Aluno.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Perfil de aluno não encontrado para o usuário logado.'}, status=403)

        # --- A PARTIR DAQUI, AVALIAÇÃO É PERMITIDA ---
        
        # 2. Cria a Avaliacao "pai"
        # CORREÇÃO: Passa o objeto 'aluno_logado' para ligar a avaliação ao aluno.
        nova_avaliacao = Avaliacao.objects.create(
            disciplina_pessoa=disciplina_pessoa,
            aluno=aluno_logado, 
            comentario=comentario_texto if comentario_texto else None # <-- AQUI ESTÁ A MUDANÇA
        )

        # 3. Busca as categorias para usar as FKs
        try:
            categorias = {
                'didatica': Categoria.objects.get(nome_categoria='Didática'),
                'dificuldade': Categoria.objects.get(nome_categoria='Dificuldade'),
                'relacionamento': Categoria.objects.get(nome_categoria='Relacionamento'),
                'pontualidade': Categoria.objects.get(nome_categoria='Pontualidade'),
            }
        except Categoria.DoesNotExist as e:
            # Garante que a transação seja desfeita se faltar categoria
            transaction.set_rollback(True) 
            return JsonResponse({'success': False, 'error': 'Categoria não encontrada no banco de dados. Contate o administrador.'}, status=500)

        # 4. Cria as AvaliacaoCategoria (as 4 notas)
        for key, categoria_obj in categorias.items():
            AvaliacaoCategoria.objects.create(
                avaliacao=nova_avaliacao, 
                categoria=categoria_obj, 
                nota=float(data.get(key))
            )
        
        return JsonResponse({'success': True})

    except DisciplinaPessoa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Disciplina inválida'}, status=404)
    except Exception as e:
        # Pega erros de JSON, conversão de float, ou outros erros inesperados
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# @require_POST
# @login_required # Garante que o usuário está logado
# def salvar_avaliacao_api(request):
#     try:
#         data = json.loads(request.body)
        
#         disciplina_pessoa_id = data.get('disciplina_pessoa_id')
#         if not disciplina_pessoa_id:
#             return JsonResponse({'success': False, 'error': 'Disciplina não selecionada'}, status=400)

#         disciplina_pessoa = DisciplinaPessoa.objects.get(pk=disciplina_pessoa_id)
        
#         # 1. Cria a Avaliacao "pai"
#         nova_avaliacao = Avaliacao.objects.create(
#             disciplina_pessoa=disciplina_pessoa
#         )

#         # 2. Busca as categorias para usar as FKs
#         try:
#             categoria_didatica = Categoria.objects.get(nome_categoria='Didática')
#             categoria_dificuldade = Categoria.objects.get(nome_categoria='Dificuldade')
#             categoria_relacionamento = Categoria.objects.get(nome_categoria='Relacionamento')
#             categoria_pontualidade = Categoria.objects.get(nome_categoria='Pontualidade')
#         except Categoria.DoesNotExist as e:
#             return JsonResponse({'success': False, 'error': f'Categoria não encontrada no banco de dados: {e}'}, status=500)

#         # 3. Cria as AvaliacaoCategoria (as 4 notas)
#         AvaliacaoCategoria.objects.create(
#             avaliacao=nova_avaliacao, 
#             categoria=categoria_didatica, 
#             nota=float(data.get('didatica'))
#         )
#         AvaliacaoCategoria.objects.create(
#             avaliacao=nova_avaliacao, 
#             categoria=categoria_dificuldade, 
#             nota=float(data.get('dificuldade'))
#         )
#         AvaliacaoCategoria.objects.create(
#             avaliacao=nova_avaliacao, 
#             categoria=categoria_relacionamento, 
#             nota=float(data.get('relacionamento'))
#         )
#         AvaliacaoCategoria.objects.create(
#             avaliacao=nova_avaliacao, 
#             categoria=categoria_pontualidade, 
#             nota=float(data.get('pontualidade'))
#         )
        
#         return JsonResponse({'success': True})

#     except DisciplinaPessoa.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'Disciplina inválida'}, status=404)
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@login_required # Garante que o usuário está logado
def salvar_comentario_api(request):
    # --- INÍCIO DA CORREÇÃO DE INDENTAÇÃO ---
    try:
        data = json.loads(request.body)

        disciplina_pessoa_id = data.get('disciplina_pessoa_id')
        texto_comentario = data.get('texto')

        if not disciplina_pessoa_id:
            return JsonResponse({'success': False, 'error': 'Disciplina não selecionada'}, status=400)
        if not texto_comentario:
            return JsonResponse({'success': False, 'error': 'Comentário não pode estar vazio'}, status=400)

        disciplina_pessoa = DisciplinaPessoa.objects.get(pk=disciplina_pessoa_id)

        # Cria uma Avaliacao apenas com o comentário
        comentario_obj = Avaliacao.objects.create(
            disciplina_pessoa=disciplina_pessoa, comentario=texto_comentario
        )
        
        # CORREÇÃO: 'return' estava escrito errado e mal indentado
        return JsonResponse({'success': True, 'timestamp': comentario_obj.data_avaliacao})

    except DisciplinaPessoa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Disciplina inválida'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
# A FUNÇÃO 'salvar_comentario_api' TERMINA AQUI.
# --- FIM DA CORREÇÃO DE INDENTAÇÃO ---


# ============================================================
# NOVA FUNÇÃO (ranking_geral) COMEÇA AQUI, FORA DA ANTERIOR
# ============================================================
# Em avaliacoes/views.py

@login_required(login_url='login')
def ranking_geral(request):
    
    # 1. Decide o limite (Top 10 para admin, Top 5 para outros)
    if request.user.is_staff:
        limite = 10
    else:
        limite = 5

    # 2. A unidade de ranking agora é a 'DisciplinaPessoa' (a turma)
    #    Anotamos a média de notas em cada 'DisciplinaPessoa'
    ranking = DisciplinaPessoa.objects.annotate(
        media_nota=Avg('avaliacoes__categorias_avaliacao__nota')
    )
    
    # 3. Lógica principal do Ranking:
    #    - Filtra para incluir apenas quem JÁ TEM avaliações (media_nota não é Nula)
    #    - Ordena pela 'media_nota' em ordem descendente
    #    - select_related otimiza a busca, pegando dados do professor e disciplina
    ranking_disciplinas = ranking.filter(
        media_nota__isnull=False
    ).select_related(
        'pessoa', 'pessoa__professor', 'disciplina'
    ).order_by('-media_nota')
    
    # 4. Limita o ranking (com o limite que definimos)
    ranking_top = ranking_disciplinas[:limite]

    context = {
        # O nome da variável mudou para refletir o que estamos enviando
        'ranking_disciplinas': ranking_top
        # O template vai usar 'request.user.is_staff' para decidir como exibir
    }
    
    return render(request, 'avaliacoes/ranking_geral.html', context)

@staff_member_required
def selecionar_professor_para_editar(request):
    professores = Professor.objects.all().select_related('user').order_by('user__first_name')
    return render(request, 'avaliacoes/selecionar_professor_para_editar.html', {
        'professores': professores
    })


@staff_member_required # Garante que só admins podem editar
def editar_professor(request, professor_id):
    # Pega os objetos principais
    professor = get_object_or_404(Professor, pk=professor_id)
    user = professor.user
    
    # Pega as disciplinas que o professor JÁ ministra
    disciplinas_atuais = DisciplinaPessoa.objects.filter(pessoa=user)

    if request.method == 'POST':
        # --- LÓGICA PARA ATUALIZAR O PERFIL ---
        if 'submit_profile' in request.POST:
            user_form = UserProfileForm(request.POST, instance=user, prefix='user')
            professor_form = ProfessorForm(request.POST, request.FILES, instance=professor, prefix='prof')
            
            if user_form.is_valid() and professor_form.is_valid():
                user_form.save()
                professor_form.save()
                messages.success(request, 'Perfil do professor atualizado com sucesso!')
                return redirect('editar_professor', professor_id=professor.id)

        # --- LÓGICA PARA ADICIONAR DISCIPLINA ---
        elif 'submit_disciplina' in request.POST:
            disciplina_form = DisciplinaPessoaForm(request.POST, prefix='disc')
            
            if disciplina_form.is_valid():
                materia = disciplina_form.cleaned_data['disciplina']
                try:
                    # Tenta criar a nova relação
                    obj, created = DisciplinaPessoa.objects.get_or_create(
                        pessoa=user,
                        disciplina=materia
                    )
                    if created:
                        messages.success(request, f"Disciplina '{materia.nome}' adicionada ao professor.")
                    else:
                        messages.warning(request, f"O professor já está cadastrado nessa disciplina.")
                except IntegrityError:
                     messages.error(request, "Erro ao tentar adicionar a disciplina.")
                
                return redirect('editar_professor', professor_id=professor.id)
        
        # --- NOVA LÓGICA DE EXCLUSÃO ---
        elif 'submit_delete' in request.POST:
            try:
                nome_professor = professor.user.get_full_name()
                # Deleta o CustomUser. O Professor profile e DisciplinaPessoa serão deletados em cascata.
                professor.user.delete() 
                messages.success(request, f"Professor '{nome_professor}' foi excluído com sucesso.")
                return redirect('lista_professores') # Redireciona para a lista de professores
            except Exception as e:
                messages.error(request, f"Erro ao excluir professor: {e}")
                return redirect('editar_professor', professor_id=professor.id)
        # --- FIM DA NOVA LÓGICA ---

    # Se for um request GET, inicializa os formulários
    else:
        user_form = UserProfileForm(instance=user, prefix='user')
        professor_form = ProfessorForm(instance=professor, prefix='prof')
        disciplina_form = DisciplinaPessoaForm(prefix='disc')

    context = {
        'professor': professor,
        'user_form': user_form,
        'professor_form': professor_form,
        'disciplina_form': disciplina_form,
        'disciplinas_atuais': disciplinas_atuais
    }
    return render(request, 'avaliacoes/editar_professor.html', context)

def sugestoes_professores_api(request):
    term = request.GET.get('term', '').strip()
    sugestoes = []
    
    # # Não busca se o termo for muito curto
    # if len(term) < 2:
    #     return JsonResponse({'sugestoes': []})
    
    # Busca por nome ou sobrenome
    professores = Professor.objects.filter(
        Q(user__first_name__icontains=term) |
        Q(user__last_name__icontains=term)
    ).select_related('user')[:10] # Limita a 10 sugestões
    
    # Cria uma lista de nomes completos, sem duplicatas
    sugestoes_set = set(prof.user.get_full_name() for prof in professores)
    
    return JsonResponse({'sugestoes': list(sugestoes_set)})

def sugestoes_disciplinas_api(request):
    term = request.GET.get('term', '').strip()
    # Se o termo for vazio, retorna lista vazia
    if not term:
        return JsonResponse({'sugestoes': []})

    normalized_term = unidecode(term).lower()
    
    # Tenta filtrar primeiro pelo campo normalizado, se ele existir
    try:
        # Se você tiver um campo customizado 'nome_normalized' no model Materia
        disciplinas = Materia.objects.filter(
            nome_normalized__icontains=normalized_term
        ).values_list('nome', flat=True)[:10]
        
    except FieldError: 
        # FieldError é o erro correto do Django quando um campo não existe no Model
        # Fallback para o campo 'nome' padrão
        disciplinas = Materia.objects.filter(
            nome__icontains=term 
        ).values_list('nome', flat=True)[:10]
    
    # Remove duplicatas e converte para lista
    sugestoes_lista = list(set(disciplinas))
    
    return JsonResponse({'sugestoes': sugestoes_lista})

@login_required(login_url='login')
def sobre_nos(request):
    """
    Renderiza a página 'Sobre Nós'.
    """
    return render(request, 'avaliacoes/sobre_nos.html')

@login_required(login_url='login')
def comparacao_disciplina(request):
    """
    Renderiza a página de comparação.
    Busca uma disciplina e calcula as médias de categoria para 
    cada professor que a ministra.
    """
    if not request.user.is_staff and request.user.user_type != 'admin':
        messages.error(request, "Acesso não autorizado. Apenas administradores podem acessar a comparação.")
        return redirect('home')
    
    query_disciplina = request.GET.get('q_disciplina', '').strip()
    context = {
        'query_disciplina': query_disciplina,
        'resultados': [],
        'materia_encontrada': None
    }

    if len(query_disciplina) > 0:
        # 1. Encontra a matéria (disciplina)
        materia = Materia.objects.filter(nome__icontains=query_disciplina).first()
        
        if materia:
            context['materia_encontrada'] = materia
            
            # 2. Encontra todos os 'DisciplinaPessoa' (professores) para essa matéria
            #    e usa annotate para calcular as médias de cada categoria
            resultados = DisciplinaPessoa.objects.filter(
                disciplina=materia
            ).select_related(
                'pessoa', 'pessoa__professor', 'disciplina'
            ).annotate(
                # Média de Didática
                media_didatica=Avg(
                    'avaliacoes__categorias_avaliacao__nota',
                    filter=Q(avaliacoes__categorias_avaliacao__categoria__nome_categoria='Didática')
                ),
                # Média de Dificuldade
                media_dificuldade=Avg(
                    'avaliacoes__categorias_avaliacao__nota',
                    filter=Q(avaliacoes__categorias_avaliacao__categoria__nome_categoria='Dificuldade')
                ),
                # Média de Relacionamento
                media_relacionamento=Avg(
                    'avaliacoes__categorias_avaliacao__nota',
                    filter=Q(avaliacoes__categorias_avaliacao__categoria__nome_categoria='Relacionamento')
                ),
                # Média de Pontualidade
                media_pontualidade=Avg(
                    'avaliacoes__categorias_avaliacao__nota',
                    filter=Q(avaliacoes__categorias_avaliacao__categoria__nome_categoria='Pontualidade')
                )
            ).filter(
                # Garante que só apareçam professores
                pessoa__user_type='professor' 
            ).order_by('pessoa__first_name') # Ordena por nome
            
            context['resultados'] = resultados
        
        else:
            if query_disciplina:
                messages.warning(request, f"Nenhuma disciplina encontrada com o termo '{query_disciplina}'.")

    return render(request, 'avaliacoes/comparacao.html', context)

def contato(request):
    # 1. LÓGICA DE ADMINISTRADOR: Vê a lista de mensagens
    if request.user.is_authenticated and hasattr(request.user, 'user_type') and request.user.user_type == 'admin':
        # Busca todas as mensagens, da mais recente para a mais antiga
        mensagens = MensagemContato.objects.all().order_by('-data_envio')
        return render(request, 'avaliacoes/admin_mensagens.html', {'mensagens': mensagens})

    # 2. LÓGICA DE USUÁRIO COMUM (Ou anônimo): Vê o formulário
    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        assunto = request.POST.get('assunto')
        mensagem = request.POST.get('mensagem')

        # Salva no banco de dados
        nova_mensagem = MensagemContato(
            nome=nome,
            email=email,
            assunto=assunto,
            mensagem=mensagem
        )
        nova_mensagem.save()
        
        messages.success(request, 'Sua mensagem foi enviada com sucesso! Em breve entraremos em contato.')
        return redirect('contato') # Recarrega a página limpa

    return render(request, 'avaliacoes/contato.html')

@staff_member_required
def selecionar_aluno_para_editar(request):
    # Busca todos os alunos ordenados pelo nome do usuário
    alunos = Aluno.objects.all().select_related('user').order_by('user__first_name')
    return render(request, 'avaliacoes/selecionar_aluno_para_editar.html', {
        'alunos': alunos
    })

@staff_member_required
def editar_aluno(request, aluno_id):
    # 1. Carregar o Aluno
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    user = aluno.user # O CustomUser ligado ao Aluno

    if request.method == 'POST':
        # --- LÓGICA DE EXCLUSÃO ---
        if 'submit_delete' in request.POST:
            try:
                nome_aluno = user.get_full_name()
                user.delete() # Deleta o CustomUser (o Aluno some em cascata)
                messages.success(request, f"Aluno '{nome_aluno}' excluído com sucesso.")
                return redirect('selecionar_aluno_para_editar')
            except Exception as e:
                messages.error(request, f"Erro ao excluir aluno: {e}")
                return redirect('editar_aluno', aluno_id=aluno.id)

        # --- LÓGICA DE EDIÇÃO (Nome/Email) ---
        elif 'submit_profile' in request.POST:
            # Assumindo que UserProfileForm é uma classe que você definiu
            user_form = UserProfileForm(request.POST, instance=user, prefix='user') 
            
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Perfil do aluno atualizado com sucesso!')
                return redirect('editar_aluno', aluno_id=aluno.id)
            else:
                messages.error(request, 'Erro ao atualizar. Verifique os campos.')

    else:
        # GET request: carrega o formulário preenchido
        # Assumindo que UserProfileForm é uma classe que você definiu
        user_form = UserProfileForm(instance=user, prefix='user') 

    # --- CARREGAMENTO DE DADOS PARA O CONTEXTO ---

    # 1. Professores (Consulta Corrigida)
    professores = CustomUser.objects.filter(user_type='professor').order_by('first_name', 'last_name')
    
    # 2. Disciplinas Atribuídas ao Aluno (Consulta Corrigida para MatriculaAluno)
    # Busca todas as matrículas do Aluno (usando o novo modelo)
    # prefetch_related para buscar os dados de Professor e Matéria em menos consultas
    matriculas_do_aluno = MatriculaAluno.objects.filter(
        aluno=aluno # Filtra pelo objeto Aluno atual
    ).select_related(
        'disciplina_professor'
    ).prefetch_related(
        'disciplina_professor__pessoa',      # O CustomUser do Professor
        'disciplina_professor__disciplina'   # O objeto Matéria/Disciplina
    ).order_by(
        'disciplina_professor__pessoa__first_name', 
        'disciplina_professor__disciplina__nome'
    )

    context = {
        'aluno': aluno,
        'user_form': user_form,
        'professores': professores, 
        # ATUALIZE o contexto para usar o nome da nova query na template
        'disciplinas_atribuidas': matriculas_do_aluno, 
    }
    # Certifique-se de que o template é 'avaliacoes/editar_aluno.html'
    return render(request, 'avaliacoes/editar_aluno.html', context)

@require_http_methods(["GET"])
def get_disciplinas_professor(request):
    professor_id = request.GET.get('professor_id')
    aluno_id = request.GET.get('aluno_id') # <-- NOVO: Capitura o ID do aluno

    if not professor_id or not aluno_id:
        return JsonResponse({'disciplinas': []})
    
    # 1. Disciplinas que o PROFESSOR leciona
    # IDs dos vínculos DisciplinaPessoa que o professor está ATIVO
    vinculos_professor_ids = DisciplinaPessoa.objects.filter(
        pessoa_id=professor_id, 
        status='ativo'
    ).values_list('id', flat=True)

    # 2. Vínculos que o ALUNO JÁ TEM
    # IDs dos vínculos DisciplinaPessoa que o aluno JÁ ESTÁ MATRICULADO
    vinculos_aluno_matriculado_ids = MatriculaAluno.objects.filter(
        aluno_id=aluno_id
    ).values_list('disciplina_professor_id', flat=True)
    
    # 3. COMBINAR FILTROS (Professor Leciona E Aluno Não Tem)
    # Busca os IDs dos vínculos que o professor leciona, 
    # EXCLUINDO aqueles que o aluno já está matriculado.
    vinculos_finais_ids = vinculos_professor_ids.exclude(
        id__in=vinculos_aluno_matriculado_ids
    ).values_list('disciplina_id', flat=True) # Retorna os IDs das Matérias (Materia.id)

    # 4. Busca os dados finais das Matérias
    disciplinas = Materia.objects.filter(
        id__in=vinculos_finais_ids
    ).values('id', 'nome').order_by('nome')
    
    return JsonResponse({'disciplinas': list(disciplinas)})

# 2. View para Adicionar Disciplina
@staff_member_required # Assumindo que apenas staff pode adicionar matrícula
@require_http_methods(["POST"])
@transaction.atomic 
def adicionar_disciplina_professor(request):
    try:
        # Tenta decodificar o JSON
        data = json.loads(request.body)
        aluno_id = data.get('aluno_id') # Recebe o ID do objeto Aluno (14)
        professor_id = data.get('professor_id') # Recebe o ID do CustomUser do professor (21)
        disciplina_id = data.get('disciplina_id')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)

    # 1. Validação de Campos
    if not aluno_id or not professor_id or not disciplina_id:
        return JsonResponse({'success': False, 'message': 'Aluno, Professor e Disciplina são obrigatórios.'}, status=400)

    try:
        # 2. Busca o Aluno (usando o modelo Aluno, que é o que o ID se refere)
        aluno = get_object_or_404(Aluno, id=aluno_id)
        
        # 3. Busca o Vínculo Professor-Disciplina (o objeto DisciplinaPessoa)
        # Verifica se o vínculo entre o CustomUser do Professor e a Matéria existe e está ativo
        disciplina_professor_vinculo = get_object_or_404(
            DisciplinaPessoa, 
            pessoa_id=professor_id, # Pessoa_id é o CustomUser.id do Professor
            disciplina_id=disciplina_id,
            status='ativo' 
        )
        
        # 4. Cria o registro de Matrícula do Aluno
        # O FK MatriculaAluno.aluno espera um objeto Aluno, que acabamos de buscar.
        MatriculaAluno.objects.create(
            aluno=aluno, # <--- OBJETO ALUNO CORRETO
            disciplina_professor=disciplina_professor_vinculo
        )

        return JsonResponse({'success': True, 'message': f'Aluno {aluno.user.get_full_name()} matriculado com sucesso na disciplina.'})
        
    except IntegrityError:
        # Pega o erro de duplicação da restrição unique_together em MatriculaAluno
        return JsonResponse({'success': False, 'message': 'O aluno já está matriculado nesta disciplina com este professor.'}, status=409)
    except Exception as e:
        # Erro genérico (ex: CustomUser ou Materia não encontrado)
        return JsonResponse({'success': False, 'message': f'Erro ao processar a matrícula: {e}'}, status=500)

# 3. View para Excluir Disciplina
@require_http_methods(["DELETE"])
def excluir_disciplina_professor(request, id):
    try:
        disciplina_pessoa = get_object_or_404(DisciplinaPessoa, id=id)
        disciplina_pessoa.delete() # Exclui do banco
        return JsonResponse({'success': True, 'message': 'Disciplina removida com sucesso.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# 4. View para Recarregar a Tabela (Renderiza o Partial Template)
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from .models import Aluno, MatriculaAluno 

@staff_member_required
@require_http_methods(["GET"])
def get_disciplinas_table(request):
    # 1. CORREÇÃO: Obter o ID do aluno, não do professor
    aluno_id = request.GET.get('aluno_id')

    if aluno_id:
        try:
            # Busca o objeto Aluno (para garantir que ele existe)
            aluno = get_object_or_404(Aluno, pk=aluno_id)
            
            # 2. CORREÇÃO: Filtrar o modelo MatriculaAluno por Aluno
            # Usamos a mesma consulta eficiente da view 'editar_aluno'
            matriculas_do_aluno = MatriculaAluno.objects.filter(
                aluno=aluno 
            ).select_related(
                'disciplina_professor'
            ).prefetch_related(
                'disciplina_professor__pessoa',     # CustomUser do Professor
                'disciplina_professor__disciplina'  # Matéria
            ).order_by(
                'disciplina_professor__pessoa__first_name', 
                'disciplina_professor__disciplina__nome'
            )
            
            # Mantemos o nome da variável para o template
            disciplinas_atribuidas = matriculas_do_aluno 
            
        except Exception:
            # Caso o Aluno não exista (embora o get_object_or_404 já cuide disso)
            disciplinas_atribuidas = MatriculaAluno.objects.none()
            
    else:
        # Se o aluno_id não for fornecido, retorna vazio
        disciplinas_atribuidas = MatriculaAluno.objects.none()
        
    # 3. Renderiza o partial
    html_table = render_to_string(
        'avaliacoes/partial_disciplinas_table.html', 
        {'disciplinas_atribuidas': disciplinas_atribuidas},
        request=request
    )
    
    return HttpResponse(html_table)

@staff_member_required
@require_http_methods(["DELETE"])
@transaction.atomic # Garante que as exclusões ocorram juntas
def excluir_matricula_aluno(request, matricula_id):
    """
    Exclui um registro de MatriculaAluno e, em cascata, remove 
    a avaliação que o aluno fez para aquela disciplina/professor.
    """
    
    try:
        matricula = get_object_or_404(MatriculaAluno, pk=matricula_id)
        
        # OBTÉM OS OBJETOS RELACIONADOS
        aluno = matricula.aluno # O Aluno que fez a matrícula
        disciplina_professor_vinculo = matricula.disciplina_professor
        
        # 1. REMOVE A AVALIAÇÃO FEITA PELO ALUNO PARA ESTE VÍNCULO
        # Isso permite que o aluno avalie novamente após a rematrícula.
        # Filtra pelo aluno e pelo vínculo DisciplinaPessoa
        avaliacoes_para_deletar = Avaliacao.objects.filter(
            aluno=aluno,
            disciplina_pessoa=disciplina_professor_vinculo
        )
        
        if avaliacoes_para_deletar.exists():
            # Deletar Avaliacao também deleta AvaliacaoCategoria em cascata
            avaliacoes_deletadas = avaliacoes_para_deletar.count()
            avaliacoes_para_deletar.delete()
        else:
            avaliacoes_deletadas = 0

        # 2. DELETA A MATRÍCULA
        matricula.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Matrícula removida com sucesso. ({avaliacoes_deletadas} avaliação(ões) limpa(s)).'
        })
        
    except Exception as e:
        # Se ocorrer um erro, a transação.atomic garante que nada será salvo/deletado
        return JsonResponse({'success': False, 'message': f'Erro ao excluir matrícula e avaliação: {e}'}, status=500)