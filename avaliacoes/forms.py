# avaliacoes/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
# Agrupei todos os imports de models em uma linha para evitar duplicação
from .models import (
    Avaliacao, Professor, Materia, AvaliacaoCategoria, 
    Categoria, DisciplinaPessoa, CustomUser
)

User = get_user_model()

# --- WIDGET PERSONALIZADO ---
class ProfessorSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                # Lógica para extrair o ID corretamente, seja de um objeto ou valor direto
                val = value
                if hasattr(value, 'instance'):
                    val = value.instance.pk
                elif hasattr(value, 'value'):
                    val = value.value()
                elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                    val = list(value)[0]
                
                # Busca o professor para pegar a URL da foto
                professor = Professor.objects.get(pk=val)
                foto_url = professor.foto.url if professor.foto else ''
                option['attrs']['data-foto-url'] = foto_url
            except (Professor.DoesNotExist, ValueError, TypeError):
                # Se der erro ou não encontrar, deixa sem foto
                option['attrs']['data-foto-url'] = ''
        return option

# --- FORMULÁRIOS DE AVALIAÇÃO ---

class AvaliacaoForm(forms.ModelForm):
    disciplina_pessoa = forms.ModelChoiceField(
        # OBS: Certifique-se que seu model tem o campo 'status', senão remova o .filter(status='ativo')
        queryset=DisciplinaPessoa.objects.all(), 
        label="Disciplina e Professor"
    )

    class Meta:
        model = Avaliacao
        fields = ['disciplina_pessoa']

class AvaliacaoCategoriaForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        label="Categoria de Avaliação"
    )
    nota = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=0,
        max_value=5,
        label="Nota (0 a 5)"
    )

    class Meta:
        model = AvaliacaoCategoria
        fields = ['categoria', 'nota']

# --- FORMULÁRIOS DE USUÁRIO (AUTH) ---

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'user_type')

    def clean_user_type(self):
        user_type = self.cleaned_data.get('user_type')
        # CORREÇÃO: Verifica se o usuário logado existe e se é staff ou admin
        if user_type == 'admin':
             # Se self.request.user não estiver disponível (ex: shell), isso pode falhar.
             # Mas em views normais funciona.
            if self.request and self.request.user:
                if not (self.request.user.is_staff or self.request.user.user_type == 'admin'):
                    raise forms.ValidationError('Apenas administradores podem criar usuários admin.')
        return user_type

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'user_type')


# --- FORMULÁRIOS DE CADASTRO GERAL ---

class MateriaForm(forms.ModelForm):
    class Meta:
        model = Materia
        fields = ['nome', 'codigo', 'data_inicio']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'})  # Input nativo do HTML5
        }

class ProfessorForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ['foto'] 

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'user_type', 'password']
        widgets = {
            'password': forms.PasswordInput(), # Oculta a senha ao digitar
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash da senha (segurança)
        if commit:
            user.save()
        return user

# --- NOVOS FORMULÁRIOS (PERFIL E DISCIPLINA) ---

class UserProfileForm(forms.ModelForm):
    """
    Formulário para editar NOME e EMAIL do usuário.
    """
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'Email de Login'
        }

class DisciplinaPessoaForm(forms.ModelForm):
    """
    Formulário para ADICIONAR uma nova disciplina a um professor.
    """
    disciplina = forms.ModelChoiceField(
        queryset=Materia.objects.all().order_by('nome'),
        label="Selecione a disciplina para adicionar"
    )

    class Meta:
        model = DisciplinaPessoa
        fields = ['disciplina']