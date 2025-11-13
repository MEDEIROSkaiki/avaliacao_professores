# Em avaliacoes/admin.py

from django.contrib import admin
# IMPORTAÇÕES ADICIONADAS:
from .models import (
    Professor, Avaliacao, Materia, Aluno, DisciplinaPessoa, 
    Categoria, AvaliacaoCategoria
)

admin.site.register(Professor)
admin.site.register(Avaliacao)
admin.site.register(Materia)
admin.site.register(Aluno)
admin.site.register(DisciplinaPessoa) # Você já deve ter feito isso

# --- ADICIONE ESTAS LINHAS ---
admin.site.register(Categoria)
admin.site.register(AvaliacaoCategoria)
# --- FIM DA ADIÇÃO ---