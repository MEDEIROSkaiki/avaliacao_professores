from django import forms
from .models import Avaliacao, Professor, Materia, AvaliacaoCategoria, Categoria, DisciplinaPessoa, CustomUser
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import CustomUser

class ProfessorSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                # Garante que value é string/int válido, extrai se for ModelChoiceIteratorValue
                val = value
                if hasattr(value, 'instance'):
                    val = value.instance.pk
                elif hasattr(value, 'value'):
                    val = value.value()
                elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                    val = list(value)[0]
                professor = Professor.objects.get(pk=val)
                foto_url = professor.foto.url if professor.foto else ''
                option['attrs']['data-foto-url'] = foto_url
            except Professor.DoesNotExist:
                option['attrs']['data-foto-url'] = ''
        return option

class AvaliacaoForm(forms.ModelForm):
    disciplina_pessoa = forms.ModelChoiceField(
        queryset=DisciplinaPessoa.objects.filter(status='ativo'),
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

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'user_type')

    def clean_user_type(self):
        user_type = self.cleaned_data.get('user_type')
        # validação: só admin cria admin
        if user_type == 'admin' and not self.request.user.is_admin():
            raise forms.ValidationError('Apenas administradores podem criar usuários admin.')
        return user_type

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'user_type')


User = get_user_model()

class MateriaForm(forms.ModelForm):
    class Meta:
        model = Materia
        fields = ['nome', 'codigo', 'data_inicio']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'})  # campo de data manual
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
            'password': forms.PasswordInput(),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # encripta a senha
        if commit:
            user.save()
        return user

# --- NOVOS FORMULÁRIOS ADICIONADOS ---

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
    # Filtra o queryset para mostrar apenas as matérias
    disciplina = forms.ModelChoiceField(
        queryset=Materia.objects.all().order_by('nome'),
        label="Selecione a disciplina para adicionar"
    )

    class Meta:
        model = DisciplinaPessoa
        fields = ['disciplina']