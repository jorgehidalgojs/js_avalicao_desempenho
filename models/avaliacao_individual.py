  # -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
class Individual(models.Model):
    _name = "avaliacao.individual"
    _description = "Avaliacao Individual"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Many2one('hr.employee', string='Nome', ondelete='cascade', required=True, tracking=True)
    cargo = fields.Many2one('hr.job', string='Cargo', related='name.job_id', related_sudo=True, store=True, tracking=True)
    departamento = fields.Many2one('hr.department', related='name.department_id', related_sudo=True, string='Departamento', store=True,tracking=True)
    avaliador = fields.Many2one('hr.employee', string='Avaliador', ondelete='cascade', required=True,tracking=True)
    cargo_avaliador = fields.Many2one('hr.job', related='avaliador.job_id', related_sudo=True, string="Cargo do Avaliador", required=True,tracking=True)
    data_aprovacao = fields.Datetime(string="Data de Aprovação", required=True, default=fields.Datetime.now,tracking=True)
    anotacoes = fields.Char(string='Anotações', required=True,tracking=True)
    status = fields.Selection(
        [('novo', 'Novo'),
         ('avaliar', 'Avaliado'),
         ('cancelar', 'Cancelado')],
        default="novo",
        string="Status", tracking=True)
    check_individual = fields.Many2many('avaliar.template', 'avaliacao_individual_template_rel', 'individual_id', 'template_individual_id', string="Tipo de competência", required=True,tracking=True)
    custom_individual_ids = fields.One2many('avaliacao.tipo', 'individual_id', string="Competências", required=True,tracking=True)

    @api.onchange('check_individual')
    def onchange_check_list(self):
        self.custom_individual_ids = [(5, 0, 0)]

        linhas = []

        competencias = self.env['avaliacaodesempenho.avaliacaodesempenho'].search([
            ('competencia_list', 'in', self.check_individual.ids)
        ])

        for item in competencias:
            linhas.append((0, 0, {
                'name': item.name,
                'description': item.description,
                'peso': item.peso,
                'escala': item.escala,
                'competencia': item.competencia_list.name,
            }))

        self.custom_individual_ids = linhas
