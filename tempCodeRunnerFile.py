    screen.fill(SKY_BLUE)
    level.platforms.draw(screen)
    level.enemies.draw(screen)
    grenade_enemies.draw(screen)  # <-- Moved up
    enemy_bullets.draw(screen)
    grenades.draw(screen)        # <-- Moved up
    explosions.draw(screen)      # <-- Moved up
    if level.goal:
        screen.blit(level.goal.image, level.goal.rect)
    bullets.draw(screen)
    player_group.draw(screen)
    draw_hud(screen, player, current_level_index)
    pygame.display.flip()