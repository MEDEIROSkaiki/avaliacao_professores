from django.db import models
from django.contrib.auth.models import AbstractUser
from unidecode import unidecode
from django.utils import timezone

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('aluno', 'Aluno'),
        ('professor', 'Professor'),
        ('admin', 'Administrador'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='aluno')
    cpf = models.CharField(max_length=11, unique=True)
    data_nascimento = models.DateField(null=True, blank=True)

    def is_admin(self):
        return self.user_type == 'admin'

    def __str__(self):
        return self.username

class Materia(models.Model):
    nome = models.CharField(max_length=100) # Este campo armazena o nome real ("Química")
    codigo = models.CharField(max_length=20, unique=True)
    data_inicio = models.DateField()
    
    # Campo auxiliar SÓ PARA BUSCA (armazena "quimica")
    # db_index=True é crucial para performance na busca.
    nome_normalized = models.CharField(max_length=100, blank=True, db_index=True) 

    def save(self, *args, **kwargs):
        # A normalização (remoção de acentos) afeta SOMENTE o campo 'nome_normalized'.
        # O campo 'self.nome' permanece inalterado.
        self.nome_normalized = unidecode(self.nome).lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
class Professor(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'professor'})
    foto = models.ImageField(upload_to='professores_fotos/', blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Aluno(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'aluno'})

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class DisciplinaPessoa(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
    ]

    disciplina = models.ForeignKey('Materia', on_delete=models.CASCADE)
    pessoa = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='disciplinas_pessoa')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')

    class Meta:
        unique_together = ('disciplina', 'pessoa')

    def __str__(self):
        return f"{self.pessoa} - {self.disciplina}"

class Categoria(models.Model):
    nome_categoria = models.CharField(max_length=50)

    def __str__(self):
        return self.nome_categoria

class Avaliacao(models.Model):
    aluno = models.ForeignKey('Aluno', on_delete=models.CASCADE, related_name='avaliacoes_feitas', null=True) 

    disciplina_pessoa = models.ForeignKey(DisciplinaPessoa, on_delete=models.CASCADE, null=True, blank=True, related_name='avaliacoes')
    data_avaliacao = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(null=True, blank=True)
    # Opcional, mas altamente recomendado para unicidade:
    class Meta:
        unique_together = ('disciplina_pessoa', 'aluno')


class AvaliacaoCategoria(models.Model):
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, related_name='categorias_avaliacao')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    nota = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        unique_together = ('avaliacao', 'categoria')

    def __str__(self):
        return f"{self.avaliacao} - {self.categoria.nome_categoria}: {self.nota}"

class MediaDisciplina(models.Model):
    disciplina_pessoa = models.ForeignKey(DisciplinaPessoa, on_delete=models.CASCADE)
    media = models.DecimalField(max_digits=4, decimal_places=2)
    qtde_avaliacoes = models.IntegerField()
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Média Disciplina {self.disciplina_pessoa}"

class MediaDisciplinaCategoria(models.Model):
    disciplina_pessoa = models.ForeignKey(DisciplinaPessoa, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    media = models.DecimalField(max_digits=4, decimal_places=2)
    qtde_avaliacoes = models.IntegerField()
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.disciplina_pessoa} - {self.categoria.nome_categoria}"

class MediaProfessor(models.Model):
    pessoa = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'professor'})
    media = models.DecimalField(max_digits=4, decimal_places=2)
    qtde_disciplinas = models.IntegerField()
    qtde_avaliacoes = models.IntegerField()
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Média Professor {self.pessoa}"

class MediaUniversidade(models.Model):
    media = models.DecimalField(max_digits=4, decimal_places=2)
    qtde_professores = models.IntegerField()
    qtde_disciplinas = models.IntegerField()
    qtde_avaliacoes = models.IntegerField()
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Média Geral da Universidade"

# No final do arquivo models.py

class MensagemContato(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    assunto = models.CharField(max_length=150)
    mensagem = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False) # Para o admin marcar se já leu

    def __str__(self):
        return f"{self.assunto} - {self.nome}"
    
class MatriculaAluno(models.Model):
    """
    Representa a matrícula de um aluno em um vínculo específico (Professor + Disciplina).
    """
    
    # 1. Aluno (agora ligado diretamente ao modelo Aluno)
    aluno = models.ForeignKey(
        Aluno, # <--- CORRIGIDO PARA ALUNO!
        on_delete=models.CASCADE, 
        related_name='matriculas',
        verbose_name='Aluno Matriculado'
    )
    
    # 2. Vínculo Professor-Disciplina (o objeto DisciplinaPessoa existente)
    disciplina_professor = models.ForeignKey(
        DisciplinaPessoa, 
        on_delete=models.CASCADE, 
        related_name='matriculas_alunos',
        verbose_name='Disciplina e Professor'
    )
    
    # 3. Campo Extra Solicitado
    data_inclusao = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Data de Matrícula'
    )

    class Meta:
        verbose_name = "Matrícula do Aluno"
        verbose_name_plural = "Matrículas dos Alunos"
        
        # Garante a unicidade: (Aluno, DisciplinaPessoa)
        unique_together = ('aluno', 'disciplina_professor')

    def __str__(self):
        # Acesso ao CustomUser através do Aluno: aluno.user
        return f"{self.aluno.user.get_full_name()} - {self.disciplina_professor}" 