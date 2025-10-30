from django import forms
from .models import Avaliacao, Professor

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
    class Meta:
        model = Avaliacao
        fields = ['professor', 'nota', 'comentario']
        widgets = {
            'professor': ProfessorSelect(),
            'nota': forms.RadioSelect(),  # Isso força exibir como rádio
            'comentario': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        }
        labels = {
            'professor': 'Selecione o Professor',
            'nota': 'Avaliação (1 a 5)',
            'comentario': 'Comentário (opcional)',
        }