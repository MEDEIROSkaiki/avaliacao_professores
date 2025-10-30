from django.db import models

from django.db import models

class Professor(models.Model):
    MATERIA_CHOICES = [
        ('BD', 'Banco de Dados'),
        ('LP', 'Logica de Programação'),
        ('AE', 'Algoritmos e Estruturas de Dados'),
        ('SO', 'Sistemas Operacionais'),
        ('DS', 'Desenvolvimento de Software'),
    ]
    nome = models.CharField(max_length=100)
    materia = models.CharField(max_length=3, choices=MATERIA_CHOICES, default='MAT')
    foto = models.ImageField(upload_to='professores_fotos/', blank=True, null=True)


    def __str__(self):
        return self.nome

class Avaliacao(models.Model):
    NOTA_CHOICES = [(i, i) for i in range(1, 6)]
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    nota = models.IntegerField(choices=NOTA_CHOICES)  # Escolhas de 1 a 5
    comentario = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)