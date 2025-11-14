import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from avaliacoes.models import (
    Materia, CustomUser, Professor, DisciplinaPessoa,
    Avaliacao, Categoria, AvaliacaoCategoria
)

# --- CONFIGURAÇÕES ---
NUM_PROFESSORES = 15
NUM_DISCIPLINAS = 10
NUM_AVALIACOES_POR_TURMA = 25 # Gera X avaliações para CADA turma

# --- DADOS FAKE ---
LISTA_DISCIPLINAS = [
    'Cálculo I', 'Álgebra Linear', 'Banco de Dados', 'Inteligência Artificial',
    'Física Moderna', 'Química Orgânica', 'Filosofia da Ciência',
    'Engenharia de Software', 'Redes de Computadores', 'Sistemas Operacionais',
    'Estrutura de Dados', 'Marketing Digital', 'Direito Constitucional',
    'Economia I', 'Literatura Brasileira'
]

class Command(BaseCommand):
    help = 'Cria uma grande quantidade de dados fake para popular o banco de dados.'

    def handle(self, *args, **options):
        # Inicia o Faker
        fake = Faker('pt_BR')
        
        # Garante que a operação inteira seja atômica
        with transaction.atomic():
            self.stdout.write(self.style.WARNING('Limpando dados antigos...'))
            
            # Limpa dados antigos (exceto superusuários)
            Materia.objects.all().delete()
            CustomUser.objects.filter(is_superuser=False).delete()
            # O resto (Professor, Avaliacao, etc) é deletado em cascata
            
            self.stdout.write(self.style.SUCCESS('Dados antigos limpos.'))
            self.stdout.write('Iniciando criação de novos dados...')

            # --- 1. Criar Categorias (Garantir que existam) ---
            cat_didatica, _ = Categoria.objects.get_or_create(nome_categoria='Didática')
            cat_dificuldade, _ = Categoria.objects.get_or_create(nome_categoria='Dificuldade')
            cat_relacionamento, _ = Categoria.objects.get_or_create(nome_categoria='Relacionamento')
            cat_pontualidade, _ = Categoria.objects.get_or_create(nome_categoria='Pontualidade')
            categorias_list = [cat_didatica, cat_dificuldade, cat_relacionamento, cat_pontualidade]

            # --- 2. Criar Disciplinas (Matérias) ---
            disciplinas_criadas = []
            disciplinas_para_criar = random.sample(LISTA_DISCIPLINAS, NUM_DISCIPLINAS)
            
            for i, nome_disc in enumerate(disciplinas_para_criar):
                codigo = f"{nome_disc[:3].upper()}{i+1:03d}"
                materia = Materia.objects.create(
                    nome=nome_disc,
                    codigo=codigo,
                    data_inicio=fake.date_between(start_date='-2y', end_date='-1y')
                )
                disciplinas_criadas.append(materia)
            
            self.stdout.write(f"-> {len(disciplinas_criadas)} Disciplinas criadas.")

            # --- 3. Criar Professores ---
            professores_criados = []
            for _ in range(NUM_PROFESSORES):
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f"{first_name.lower()}.{last_name.lower()}_{fake.random_int(1,99)}@eduavalia.com"
                
                try:
                    user = CustomUser.objects.create_user(
                        username=email,
                        email=email,
                        password='123',
                        user_type='professor',
                        first_name=first_name,
                        last_name=last_name,
                        cpf=fake.cpf().replace('.', '').replace('-', ''),
                        data_nascimento=fake.date_of_birth(minimum_age=25, maximum_age=65)
                    )
                    prof = Professor.objects.create(user=user)
                    professores_criados.append(prof)
                except Exception as e:
                    # Se o CPF/Email já existir, apenas ignora e continua
                    self.stdout.write(self.style.ERROR(f'Erro ao criar professor {email}: {e}'))

            self.stdout.write(f"-> {len(professores_criados)} Professores criados.")

            # --- 4. Ligar Professores a Disciplinas (DisciplinaPessoa) ---
            turmas_criadas = []
            for prof in professores_criados:
                # Cada professor vai dar 1 ou 2 disciplinas
                num_disciplinas = random.randint(1, 2)
                disciplinas_sorteadas = random.sample(disciplinas_criadas, num_disciplinas)
                
                for disc in disciplinas_sorteadas:
                    # === REMOVIDO 'ano' E 'semestre' DAQUI ===
                    turma = DisciplinaPessoa.objects.create(
                        disciplina=disc,
                        pessoa=prof.user,
                        status='ativo'
                    )
                    turmas_criadas.append(turma)

            self.stdout.write(f"-> {len(turmas_criadas)} Turmas (DisciplinaPessoa) criadas.")

            # --- 5. Criar Avaliações e Comentários ---
            total_avaliacoes = 0
            total_comentarios = 0
            
            if not turmas_criadas:
                self.stdout.write(self.style.ERROR("Nenhuma turma foi criada, não é possível gerar avaliações."))
                return

            for turma in turmas_criadas:
                for _ in range(NUM_AVALIACOES_POR_TURMA):
                    
                    # 1. Cria a Avaliação "pai"
                    avaliacao = Avaliacao.objects.create(
                        disciplina_pessoa=turma,
                        data_avaliacao=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=None)
                    )
                    
                    # 2. Adiciona um comentário em ~50% dos casos
                    if random.choice([True, False]):
                        avaliacao.comentario = fake.paragraph(nb_sentences=random.randint(2, 4))
                        avaliacao.save()
                        total_comentarios += 1

                    # 3. Cria as 4 notas (AvaliacaoCategoria)
                    
                    # Função para gerar nota com passo de 0.5
                    def get_random_nota(min_val, max_val):
                        # Garante que a nota esteja no formato X.X ou X.5
                        nota = round(random.uniform(min_val, max_val) * 2) / 2
                        # Garante que a nota não passe de 10.0
                        return min(nota, 10.0)

                    AvaliacaoCategoria.objects.create(
                        avaliacao=avaliacao,
                        categoria=cat_didatica,
                        nota=get_random_nota(4.0, 10.0) # Professores geralmente têm didática boa
                    )
                    AvaliacaoCategoria.objects.create(
                        avaliacao=avaliacao,
                        categoria=cat_dificuldade,
                        nota=get_random_nota(2.0, 9.0) # Dificuldade é variada
                    )
                    AvaliacaoCategoria.objects.create(
                        avaliacao=avaliacao,
                        categoria=cat_relacionamento,
                        nota=get_random_nota(5.0, 10.0)
                    )
                    AvaliacaoCategoria.objects.create(
                        avaliacao=avaliacao,
                        categoria=cat_pontualidade,
                        nota=get_random_nota(7.0, 10.0) # Pontualidade geralmente alta
                    )
                    total_avaliacoes += 1

            self.stdout.write(f"-> {total_avaliacoes} Avaliações criadas.")
            self.stdout.write(f"-> {total_comentarios} Comentários criados.")
            
            self.stdout.write(self.style.SUCCESS(
                f"\n=== POVOAMENTO DE DADOS CONCLUÍDO ==="
            ))