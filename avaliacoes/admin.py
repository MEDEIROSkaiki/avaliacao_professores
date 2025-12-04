from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Professor, Aluno, Materia, DisciplinaPessoa, 
    Categoria, Avaliacao, AvaliacaoCategoria
)

# Importações necessárias para o envio de e-mail e geração de link
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings

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

    def save_model(self, request, obj, form, change):
        """
        Sobrescreve o método de salvar para enviar e-mail quando um novo usuário é criado.
        """
        # Verifica se é um usuário novo (não tem ID ainda)
        eh_novo = not obj.pk
        
        # Salva o usuário primeiro para gerar o ID e garantir que ele existe no banco
        super().save_model(request, obj, form, change)

        if eh_novo:
            # Lista de tipos que devem receber o e-mail
            tipos_permitidos = ['aluno', 'professor', 'admin']
            
            # Verifica se o tipo do usuário está na lista OU se ele é Staff/Superuser (Admin)
            # Adapte 'admin' caso seu user_type para administrador tenha outro nome
            if obj.user_type in tipos_permitidos or obj.is_staff or obj.is_superuser:
                self.enviar_email_convite(request, obj)

    def enviar_email_convite(self, request, user):
        """
        Gera o token de reset de senha e envia o e-mail de boas-vindas.
        """
        try:
            # Gera o token e o ID codificado
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Cria o link completo para a página de definir senha
            # 'password_reset_confirm' é uma URL padrão do Django Auth
            link = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )

            subject = 'Bem-vindo ao Sistema de Avaliação - Defina sua Senha'
            message = f"""
            Olá {user.first_name or user.username},

            Seu cadastro foi realizado com sucesso no sistema como {user.get_user_type_display() if hasattr(user, 'get_user_type_display') else user.user_type}.

            Para acessar a plataforma, por favor, clique no link abaixo e defina sua senha pessoal:

            {link}

            Atenciosamente,
            Equipe de Administração
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            self.message_user(request, f"E-mail de convite enviado com sucesso para {user.email}")
            
        except Exception as e:
            self.message_user(request, f"Erro ao enviar e-mail para {user.email}: {str(e)}", level='error')

# --- REGISTROS ---

# Registra seu CustomUser com a classe personalizada
admin.site.register(CustomUser, CustomUserAdmin)

# Registra todos os seus outros modelos
admin.site.register(Professor)
admin.site.register(Aluno)
admin.site.register(Materia)
admin.site.register(DisciplinaPessoa)
admin.site.register(Categoria)
admin.site.register(Avaliacao)
admin.site.register(AvaliacaoCategoria)