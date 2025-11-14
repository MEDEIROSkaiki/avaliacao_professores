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
    Aluno, Categoria, AvaliacaoCategoria
)
from django.db.models import Avg, Count, Q
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.contrib import messages
from datetime import datetime
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import IntegrityError # Import adicionado


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
        'media_geral_faculdade': media_geral,
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
    # Inicia a query base de professores
    professores = Professor.objects.annotate(
        media_nota=Avg('user__disciplinas_pessoa__avaliacoes__categorias_avaliacao__nota')
    ).filter(id__isnull=False).order_by('user__first_name') # Adicionei ordenação

    # --- LÓGICA DE PESQUISA ---
    # Pega os termos de pesquisa da URL (vindos do GET da home)
    query_professor = request.GET.get('q_professor')
    query_disciplina = request.GET.get('q_disciplina')

    if query_professor:
        # Filtra por nome OU sobrenome
        professores = professores.filter(
            Q(user__first_name__icontains=query_professor) | 
            Q(user__last_name__icontains=query_professor)
        )

    if query_disciplina:
        # Filtra pelo nome da disciplina que o professor leciona
        professores = professores.filter(
            user__disciplinas_pessoa__disciplina__nome__icontains=query_disciplina
        ).distinct() # .distinct() evita professores duplicados se ele der 2x a mesma matéria

    context = {
        'professores': professores,
        'query_professor': query_professor, # Bônus: envia o termo de volta
        'query_disciplina': query_disciplina # Bônus: envia o termo de volta
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
        senha = 'mudaragora' 
        
        # NOVO: Captura do ID da matéria
        materia_id = request.POST.get('materia_disciplina')

        # --- 2. BLOCO DE VALIDAÇÃO (AJUSTADO) ---
        if not tipo:
            messages.error(request, "O campo 'Tipo de Usuário' é obrigatório.")
            return redirect('adicionar_usuario') # NOVO: Redireciona em vez de renderizar
        if not nome:
            messages.error(request, "O campo 'Nome Completo' é obrigatório.")
            return redirect('adicionar_usuario')
        if not email:
            messages.error(request, "O campo 'Email (login)' é obrigatório.")
            return redirect('adicionar_usuario')
            
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Email inválido. Por favor, insira um email válido.")
            return redirect('adicionar_usuario') 
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email já cadastrado. Por favor, utilize outro email.")
            return redirect('adicionar_usuario')

        # 2b. Validação do CPF (Formato e Unicidade)
        if not cpf or not cpf.isdigit() or len(cpf) != 11:
            messages.error(request, "CPF inválido. Deve conter exatamente 11 dígitos numéricos.")
            return redirect('adicionar_usuario')

        if CustomUser.objects.filter(cpf=cpf).exists():
            messages.error(request, "CPF já cadastrado. Por favor, utilize outro CPF.")
            return redirect('adicionar_usuario')

        data_nascimento_obj = None
        if data_nascimento_str:
            try:
                data_nascimento_obj = datetime.strptime(data_nascimento_str, '%d/%m/%Y').date()
            except ValueError:
                messages.error(request, "Data de Nascimento inválida. O formato deve ser DD/MM/AAAA.")
                return redirect('adicionar_usuario')
        else:
            messages.error(request, "Data de Nascimento é um campo obrigatório.")
            return redirect('adicionar_usuario')
            
        # NOVO: Validação de Matéria (apenas se for professor)
        materia_obj = None
        if tipo == 'professor':
            if not materia_id:
                messages.error(request, "Para cadastrar um Professor, a disciplina é obrigatória.")
                return redirect('adicionar_usuario')
            try:
                materia_obj = Materia.objects.get(pk=materia_id)
            except Materia.DoesNotExist:
                messages.error(request, "Disciplina selecionada inválida.")
                return redirect('adicionar_usuario')


        # --- 3. PROCESSAMENTO E SALVAMENTO ---
        nome_completo_lista = nome.split(' ')
        first_name = nome_completo_lista[0] if nome_completo_lista else ''
        last_name = ' '.join(nome_completo_lista[1:]) if len(nome_completo_lista) > 1 else ''

        try:
            novo_user = CustomUser.objects.create_user(
                username=email, 
                email=email,
                password=senha,
                user_type=tipo, 
                cpf=cpf,
                data_nascimento=data_nascimento_obj,
                is_active=True,
                first_name=first_name,
                last_name=last_name
            )
        except Exception as e:
            messages.error(request, f"Erro interno ao criar o usuário base: {e}")
            return redirect('adicionar_usuario')

        try:
            if tipo == 'professor':
                Professor.objects.create(
                    user=novo_user,
                    foto=imagem_perfil
                )
                # NOVO: Cria o link entre o professor (pessoa) e a disciplina
                DisciplinaPessoa.objects.create(
                    disciplina=materia_obj,
                    pessoa=novo_user
                    # status='ativo' será pego do default do model
                )
                messages.success(request, f"Professor {nome} cadastrado com sucesso!")
                return redirect('lista_professores') 

            elif tipo == 'aluno':
                Aluno.objects.create(
                    user=novo_user
                )
                messages.success(request, f"Aluno {nome} cadastrado com sucesso!")
                return redirect('adicionar_usuario') 
            
            elif tipo == 'administrador':
                novo_user.is_staff = True
                novo_user.is_superuser = True 
                novo_user.save()
                messages.success(request, f"Administrador {nome} cadastrado com sucesso!")
                return redirect('adicionar_usuario')

        except Exception as e:
            novo_user.delete() 
            messages.error(request, f"Erro interno ao salvar o perfil do usuário: {e}")
            return redirect('adicionar_usuario') 

    # --- Se for um GET (Carregamento da página) ---
    # NOVO: Buscar todas as matérias para o dropdown
    materias = Materia.objects.all().order_by('nome')
    context = {
        'materias': materias
    }
    return render(request, 'avaliacoes/adicionar_usuario.html', context)
            

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

    # 4. === NOVO: Lógica do Gráfico por Disciplina ===
    
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
            'dados_grafico_json': json.dumps({'all': dados_all}), # Envia ao menos o 'all' vazio
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
    }

    return render(request, 'avaliacoes/detalhes_professor.html', context)

@require_POST
@login_required # Garante que o usuário está logado
def salvar_avaliacao_api(request):
    try:
        data = json.loads(request.body)
        
        disciplina_pessoa_id = data.get('disciplina_pessoa_id')
        if not disciplina_pessoa_id:
            return JsonResponse({'success': False, 'error': 'Disciplina não selecionada'}, status=400)

        disciplina_pessoa = DisciplinaPessoa.objects.get(pk=disciplina_pessoa_id)
        
        # 1. Cria a Avaliacao "pai"
        nova_avaliacao = Avaliacao.objects.create(
            disciplina_pessoa=disciplina_pessoa
        )

        # 2. Busca as categorias para usar as FKs
        try:
            categoria_didatica = Categoria.objects.get(nome_categoria='Didática')
            categoria_dificuldade = Categoria.objects.get(nome_categoria='Dificuldade')
            categoria_relacionamento = Categoria.objects.get(nome_categoria='Relacionamento')
            categoria_pontualidade = Categoria.objects.get(nome_categoria='Pontualidade')
        except Categoria.DoesNotExist as e:
            return JsonResponse({'success': False, 'error': f'Categoria não encontrada no banco de dados: {e}'}, status=500)

        # 3. Cria as AvaliacaoCategoria (as 4 notas)
        AvaliacaoCategoria.objects.create(
            avaliacao=nova_avaliacao, 
            categoria=categoria_didatica, 
            nota=float(data.get('didatica'))
        )
        AvaliacaoCategoria.objects.create(
            avaliacao=nova_avaliacao, 
            categoria=categoria_dificuldade, 
            nota=float(data.get('dificuldade'))
        )
        AvaliacaoCategoria.objects.create(
            avaliacao=nova_avaliacao, 
            categoria=categoria_relacionamento, 
            nota=float(data.get('relacionamento'))
        )
        AvaliacaoCategoria.objects.create(
            avaliacao=nova_avaliacao, 
            categoria=categoria_pontualidade, 
            nota=float(data.get('pontualidade'))
        )
        
        return JsonResponse({'success': True})

    except DisciplinaPessoa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Disciplina inválida'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


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
    
    # 1. A unidade de ranking agora é a 'DisciplinaPessoa' (a turma)
    #    Anotamos a média de notas em cada 'DisciplinaPessoa'
    ranking = DisciplinaPessoa.objects.annotate(
        media_nota=Avg('avaliacoes__categorias_avaliacao__nota')
    )
    
    # 2. Lógica principal do Ranking:
    #    - Filtra para incluir apenas quem JÁ TEM avaliações (media_nota não é Nula)
    #    - Ordena pela 'media_nota' em ordem descendente
    #    - select_related otimiza a busca, pegando dados do professor e disciplina
    ranking_disciplinas = ranking.filter(
        media_nota__isnull=False
    ).select_related(
        'pessoa', 'pessoa__professor', 'disciplina'
    ).order_by('-media_nota')
    
    # 3. Limita o ranking (ex: Top 10)
    ranking_top_10 = ranking_disciplinas[:10]

    context = {
        # O nome da variável mudou para refletir o que estamos enviando
        'ranking_disciplinas': ranking_top_10
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
    normalized_term = unidecode(term).lower()
    
    
    try:
        disciplinas = Materia.objects.filter(
            nome_normalized__icontains=normalized_term
        ).values_list('nome', flat=True)[:10] 
        
    except AttributeError:
        disciplinas = Materia.objects.filter(
            nome__icontains=term 
        ).values_list('nome', flat=True)[:10]
    
    sugestoes_set = set(disciplinas)
    
    return JsonResponse({'sugestoes': list(sugestoes_set)})