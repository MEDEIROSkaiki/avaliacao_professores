from django.db import models
from django.contrib.auth.models import AbstractUser

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
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    data_inicio = models.DateField()

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
    disciplina_pessoa = models.ForeignKey(DisciplinaPessoa, on_delete=models.CASCADE, null=True, blank=True, related_name='avaliacoes')
    data_avaliacao = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Avaliação {self.id} - {self.disciplina_pessoa}"

class AvaliacaoCategoria(models.Model):
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, related_name='categorias_avaliacao')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    nota = models.DecimalField(max_digits=3, decimal_places=2)

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
