# avaliacoes/urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),  # raiz que decide para onde ir
    path('home/', views.home, name='home'),  # home protege com login_required
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('professores/', views.lista_professores, name='lista_professores'),
    path('professores/<int:professor_id>/', views.detalhes_professor, name='detalhes_professor'),

    # --- NOVAS URLS DE EDIÇÃO ---
    path('professores/<int:professor_id>/editar/', views.editar_professor, name='editar_professor'),
    path('professores/selecionar/', views.selecionar_professor_para_editar, name='selecionar_professor_para_editar'),
    # --- FIM ---

    path('api/salvar-avaliacao/', views.salvar_avaliacao_api, name='salvar_avaliacao_api'),
    path('api/salvar-comentario/', views.salvar_comentario_api, name='salvar_comentario_api'),

    path('api/sugestoes-professores/', views.sugestoes_professores_api, name='sugestoes_professores_api'),
    path('api/sugestoes-disciplinas/', views.sugestoes_disciplinas_api, name='sugestoes_disciplinas_api'),

    path('avaliar/', views.enviar_avaliacao, name='enviar_avaliacao'),
    path('obrigado/', views.obrigado, name='obrigado'),

    path('dashboard_grafico/', views.dashboard_grafico, name='dashboard_grafico'),
    path('comentarios/', views.lista_comentarios, name='lista_comentarios'),
    path('painel/admin_cadastro/', views.admin_cadastro, name='admin_cadastro'),

    path('disciplina/adicionar/', views.adicionar_disciplina, name='adicionar_disciplina'),
    path('usuario/adicionar/', views.adicionar_usuario, name='adicionar_usuario'),
    path('professores/', views.lista_professores, name='lista_professores'), # <-- Você tem essa rota duplicada

    path('professores/<int:professor_id>/', views.detalhes_professor, name='detalhes_professor'), # <-- E essa também
    path('ranking/', views.ranking_geral, name='ranking_geral'),
    
    # === NOVA ROTA ADICIONADA ===
    path('comparacao/', views.comparacao_disciplina, name='comparacao_disciplina'),
    # ============================
    
    path('sobre-nos/', views.sobre_nos, name='sobre_nos'),

    path('contato/', views.contato, name='contato'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='avaliacoes/password_reset_confirm.html'), 
         name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='avaliacoes/password_reset_complete.html'), 
         name='password_reset_complete'),

     path('alunos/selecionar/', views.selecionar_aluno_para_editar, name='selecionar_aluno_para_editar'),
     path('alunos/<int:aluno_id>/editar/', views.editar_aluno, name='editar_aluno'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)