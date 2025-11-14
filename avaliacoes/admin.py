from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Professor, Aluno, Materia, DisciplinaPessoa, 
    Categoria, Avaliacao, AvaliacaoCategoria
)

# Esta classe diz ao Admin como mostrar seu CustomUser
class CustomUserAdmin(UserAdmin):
    # Copia os campos do UserAdmin padrão e adiciona os seus
    fieldsets = UserAdmin.fieldsets + (
        ('Campos Personalizados', {
            'fields': ('user_type', 'cpf', 'data_nascimento'),
        }),
    )
    
    # Adiciona seus campos na tela de criação de usuário
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Campos Personalizados', {
            'fields': ('user_type', 'cpf', 'data_nascimento', 'first_name', 'last_name', 'email'),
        }),
    )
    
    # Adiciona 'user_type' na lista de usuários
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'user_type')

# --- REGISTROS ---

# Registra seu CustomUser com a classe personalizada
admin.site.register(CustomUser, CustomUserAdmin)

# Registra todos os seus outros modelos (alguns podem já estar aqui)
admin.site.register(Professor)
admin.site.register(Aluno)
admin.site.register(Materia)
admin.site.register(DisciplinaPessoa)
admin.site.register(Categoria)
admin.site.register(Avaliacao)
admin.site.register(AvaliacaoCategoria)